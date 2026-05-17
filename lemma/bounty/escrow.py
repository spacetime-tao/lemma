"""Bittensor EVM escrow helpers for Lemma bounty claims."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

BITTENSOR_EVM_TESTNET_RPC_URL = "https://test.chain.opentensor.ai"
BITTENSOR_EVM_MAINNET_RPC_URL = "https://lite.chain.opentensor.ai"
BITTENSOR_EVM_TESTNET_CHAIN_ID = 945
BITTENSOR_EVM_MAINNET_CHAIN_ID = 964
LEMMA_BOUNTY_COMMITMENT_MAGIC = b"LemmaBountyCommitmentV1"
LEMMA_BOUNTY_IDENTITY_MAGIC = b"LemmaBountyIdentityBindingV1"

_HEX_32_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{64}$")
_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")


class EscrowError(RuntimeError):
    """Raised when escrow data cannot be built or read."""


@dataclass(frozen=True)
class EscrowCommitment:
    bounty_id: str
    chain_id: int
    contract_address: str
    escrow_bounty_id: int
    claimant_evm_address: str
    payout_evm_address: str
    submitter_hotkey_pubkey: str
    artifact_sha256: str
    salt: str
    commitment_hash: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "type": "lemma_bounty_commitment_v1",
            "bounty_id": self.bounty_id,
            "chain_id": self.chain_id,
            "contract_address": self.contract_address,
            "escrow_bounty_id": self.escrow_bounty_id,
            "claimant_evm_address": self.claimant_evm_address,
            "payout_evm_address": self.payout_evm_address,
            "submitter_hotkey_pubkey": self.submitter_hotkey_pubkey,
            "artifact_sha256": self.artifact_sha256,
            "salt": self.salt,
            "commitment_hash": self.commitment_hash,
        }


def _keccak256(data: bytes) -> bytes:
    try:
        from Crypto.Hash import keccak
    except Exception as e:  # noqa: BLE001
        raise EscrowError("keccak support is unavailable; install the bundled crypto dependencies") from e
    h = keccak.new(digest_bits=256)
    h.update(data)
    return h.digest()


def _selector(signature: str) -> bytes:
    return _keccak256(signature.encode("ascii"))[:4]


def _strip_0x(value: str) -> str:
    raw = value.strip()
    return raw[2:] if raw.lower().startswith("0x") else raw


def normalize_bytes32(value: str, *, field: str) -> str:
    raw = value.strip()
    if not _HEX_32_RE.fullmatch(raw):
        raise EscrowError(f"{field} must be 32 bytes as 64 hex chars")
    return "0x" + _strip_0x(raw).lower()


def normalize_evm_address(value: str, *, field: str = "address") -> str:
    raw = value.strip()
    if not _ADDRESS_RE.fullmatch(raw):
        raise EscrowError(f"{field} must be an EVM H160 address like 0x...")
    return raw.lower()


def bytes32_from_text(value: str) -> str:
    return "0x" + _keccak256(value.encode("utf-8")).hex()


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def proof_artifact_sha256(path: Path) -> str:
    try:
        return sha256_hex(path.read_bytes())
    except OSError as e:
        raise EscrowError(f"could not read proof artifact {path}: {e}") from e


def commitment_hash(
    *,
    theorem_id: str,
    claimant_evm_address: str,
    artifact_sha256: str,
    salt: str,
    toolchain_id: str,
    policy_version: str,
    registry_sha256: str,
    payout_evm_address: str,
    submitter_hotkey_pubkey: str,
) -> str:
    """Return the Solidity-compatible commitment hash for ``LemmaBountyEscrow``."""
    parts = (
        bytes.fromhex(_strip_0x(normalize_bytes32(theorem_id, field="theorem_id"))),
        bytes.fromhex(_strip_0x(normalize_evm_address(claimant_evm_address, field="claimant_evm_address"))),
        bytes.fromhex(_strip_0x(normalize_bytes32(artifact_sha256, field="artifact_sha256"))),
        bytes.fromhex(_strip_0x(normalize_bytes32(salt, field="salt"))),
        bytes.fromhex(_strip_0x(normalize_bytes32(toolchain_id, field="toolchain_id"))),
        bytes.fromhex(_strip_0x(normalize_bytes32(policy_version, field="policy_version"))),
        bytes.fromhex(_strip_0x(normalize_bytes32(registry_sha256, field="registry_sha256"))),
        bytes.fromhex(_strip_0x(normalize_evm_address(payout_evm_address, field="payout_evm_address"))),
        bytes.fromhex(_strip_0x(normalize_bytes32(submitter_hotkey_pubkey, field="submitter_hotkey_pubkey"))),
    )
    return "0x" + _keccak256(b"".join(parts)).hex()


def bounty_identity_binding_message(
    *,
    bounty_id: str,
    registry_sha256: str,
    claimant_evm_address: str,
    payout_evm_address: str,
    artifact_sha256: str,
    commitment_hash_hex: str,
) -> bytes:
    payload = {
        "artifact_sha256": normalize_bytes32(artifact_sha256, field="artifact_sha256"),
        "bounty_id": bounty_id,
        "claimant_evm_address": normalize_evm_address(claimant_evm_address, field="claimant_evm_address"),
        "commitment_hash": normalize_bytes32(commitment_hash_hex, field="commitment_hash"),
        "payout_evm_address": normalize_evm_address(payout_evm_address, field="payout_evm_address"),
        "registry_sha256": normalize_bytes32(registry_sha256, field="registry_sha256"),
    }
    return LEMMA_BOUNTY_IDENTITY_MAGIC + b"\n" + json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _encode_uint(value: int) -> bytes:
    if value < 0:
        raise EscrowError("uint value cannot be negative")
    return int(value).to_bytes(32, "big")


def _encode_bytes32(value: str) -> bytes:
    return bytes.fromhex(_strip_0x(normalize_bytes32(value, field="bytes32"))).rjust(32, b"\x00")


def _encode_address(value: str) -> bytes:
    return bytes.fromhex(_strip_0x(normalize_evm_address(value))).rjust(32, b"\x00")


def encode_commit_proof_call(escrow_bounty_id: int, commitment_hash_hex: str) -> str:
    data = (
        _selector("commitProof(uint256,bytes32)")
        + _encode_uint(escrow_bounty_id)
        + _encode_bytes32(commitment_hash_hex)
    )
    return "0x" + data.hex()


def encode_reveal_proof_call(
    *,
    escrow_bounty_id: int,
    commitment_hash_hex: str,
    artifact_sha256: str,
    salt: str,
    payout_evm_address: str,
    submitter_hotkey_pubkey: str,
) -> str:
    data = (
        _selector("revealProof(uint256,bytes32,bytes32,bytes32,address,bytes32)")
        + _encode_uint(escrow_bounty_id)
        + _encode_bytes32(commitment_hash_hex)
        + _encode_bytes32(artifact_sha256)
        + _encode_bytes32(salt)
        + _encode_address(payout_evm_address)
        + _encode_bytes32(submitter_hotkey_pubkey)
    )
    return "0x" + data.hex()


def build_commitment(
    *,
    bounty_id: str,
    chain_id: int,
    contract_address: str,
    escrow_bounty_id: int,
    theorem_id: str,
    claimant_evm_address: str,
    payout_evm_address: str,
    artifact_sha256: str,
    salt: str,
    toolchain_id: str,
    policy_version: str,
    registry_sha256: str,
    submitter_hotkey_pubkey: str,
) -> EscrowCommitment:
    digest = commitment_hash(
        theorem_id=theorem_id,
        claimant_evm_address=claimant_evm_address,
        artifact_sha256=artifact_sha256,
        salt=salt,
        toolchain_id=toolchain_id,
        policy_version=policy_version,
        registry_sha256=registry_sha256,
        payout_evm_address=payout_evm_address,
        submitter_hotkey_pubkey=submitter_hotkey_pubkey,
    )
    return EscrowCommitment(
        bounty_id=bounty_id,
        chain_id=int(chain_id),
        contract_address=normalize_evm_address(contract_address, field="contract_address"),
        escrow_bounty_id=int(escrow_bounty_id),
        claimant_evm_address=normalize_evm_address(claimant_evm_address, field="claimant_evm_address"),
        payout_evm_address=normalize_evm_address(payout_evm_address, field="payout_evm_address"),
        submitter_hotkey_pubkey=normalize_bytes32(submitter_hotkey_pubkey, field="submitter_hotkey_pubkey"),
        artifact_sha256=normalize_bytes32(artifact_sha256, field="artifact_sha256"),
        salt=normalize_bytes32(salt, field="salt"),
        commitment_hash=digest,
    )


class BountyEscrowClient:
    """Small JSON-RPC helper for unsigned Bittensor EVM escrow interactions."""

    def __init__(self, *, rpc_url: str, contract_address: str, timeout_s: float = 30.0) -> None:
        self.rpc_url = rpc_url.rstrip("/")
        self.contract_address = normalize_evm_address(contract_address, field="contract_address")
        self.timeout_s = float(timeout_s)
        self._next_id = 1

    def _rpc(self, method: str, params: list[Any]) -> Any:
        payload = {"jsonrpc": "2.0", "id": self._next_id, "method": method, "params": params}
        self._next_id += 1
        try:
            response = httpx.post(self.rpc_url, json=payload, timeout=self.timeout_s)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise EscrowError(f"escrow RPC failed: {e}") from e
        data = response.json()
        if "error" in data:
            raise EscrowError(f"escrow RPC error: {data['error']}")
        return data.get("result")

    def eth_call(self, data: str) -> str:
        result = self._rpc("eth_call", [{"to": self.contract_address, "data": data}, "latest"])
        if not isinstance(result, str):
            raise EscrowError("escrow RPC returned non-hex eth_call result")
        return result

    def bounty_count(self) -> int:
        data = "0x" + _selector("bountyCount()").hex()
        result = self.eth_call(data)
        return int(_strip_0x(result) or "0", 16)

    def commit_transaction(self, *, escrow_bounty_id: int, commitment_hash_hex: str) -> dict[str, Any]:
        return {
            "to": self.contract_address,
            "data": encode_commit_proof_call(escrow_bounty_id, commitment_hash_hex),
            "value": "0x0",
        }

    def reveal_transaction(
        self,
        *,
        escrow_bounty_id: int,
        commitment_hash_hex: str,
        artifact_sha256: str,
        salt: str,
        payout_evm_address: str,
        submitter_hotkey_pubkey: str,
    ) -> dict[str, Any]:
        return {
            "to": self.contract_address,
            "data": encode_reveal_proof_call(
                escrow_bounty_id=escrow_bounty_id,
                commitment_hash_hex=commitment_hash_hex,
                artifact_sha256=artifact_sha256,
                salt=salt,
                payout_evm_address=payout_evm_address,
                submitter_hotkey_pubkey=submitter_hotkey_pubkey,
            ),
            "value": "0x0",
        }
