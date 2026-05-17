import hashlib
import json
from pathlib import Path

from lemma.bounty.client import load_registry
from lemma.bounty.escrow import (
    BITTENSOR_EVM_TESTNET_CHAIN_ID,
    bounty_identity_binding_message,
    build_commitment,
    commitment_hash,
    encode_commit_proof_call,
    encode_reveal_proof_call,
    proof_artifact_sha256,
)

THEOREM_ID = "0x" + "11" * 32
ARTIFACT_HASH = "0x" + "22" * 32
SALT = "0x" + "33" * 32
TOOLCHAIN_ID = "0x" + "44" * 32
POLICY_VERSION = "0x" + "55" * 32
REGISTRY_SHA = "0x" + "66" * 32
HOTKEY_PUBKEY = "0x" + "77" * 32
CLAIMANT = "0x" + "88" * 20
PAYOUT = "0x" + "99" * 20
CONTRACT = "0x" + "aa" * 20


def test_commitment_hash_is_stable() -> None:
    digest = commitment_hash(
        theorem_id=THEOREM_ID,
        claimant_evm_address=CLAIMANT,
        artifact_sha256=ARTIFACT_HASH,
        salt=SALT,
        toolchain_id=TOOLCHAIN_ID,
        policy_version=POLICY_VERSION,
        registry_sha256=REGISTRY_SHA,
        payout_evm_address=PAYOUT,
        submitter_hotkey_pubkey=HOTKEY_PUBKEY,
    )

    assert digest == "0x0160801f1f17b08f5d570b04634bad6d649409049cae3091fcfa9b7a9b121976"


def test_build_commitment_normalizes_fields() -> None:
    package = build_commitment(
        bounty_id="fc.test",
        chain_id=BITTENSOR_EVM_TESTNET_CHAIN_ID,
        contract_address=CONTRACT.upper().replace("X", "x"),
        escrow_bounty_id=12,
        theorem_id=THEOREM_ID,
        claimant_evm_address=CLAIMANT,
        payout_evm_address=PAYOUT,
        artifact_sha256=ARTIFACT_HASH,
        salt=SALT,
        toolchain_id=TOOLCHAIN_ID,
        policy_version=POLICY_VERSION,
        registry_sha256=REGISTRY_SHA,
        submitter_hotkey_pubkey=HOTKEY_PUBKEY,
    )

    payload = package.as_dict()
    assert payload["type"] == "lemma_bounty_commitment_v1"
    assert payload["chain_id"] == 945
    assert payload["contract_address"] == CONTRACT
    assert payload["escrow_bounty_id"] == 12
    assert payload["commitment_hash"].startswith("0x")


def test_identity_binding_message_is_canonical() -> None:
    msg_a = bounty_identity_binding_message(
        bounty_id="fc.test",
        registry_sha256=REGISTRY_SHA,
        claimant_evm_address=CLAIMANT,
        payout_evm_address=PAYOUT,
        artifact_sha256=ARTIFACT_HASH,
        commitment_hash_hex="0x" + "ab" * 32,
    )
    msg_b = bounty_identity_binding_message(
        commitment_hash_hex="0x" + "ab" * 32,
        artifact_sha256=ARTIFACT_HASH,
        payout_evm_address=PAYOUT,
        claimant_evm_address=CLAIMANT,
        registry_sha256=REGISTRY_SHA,
        bounty_id="fc.test",
    )

    assert msg_a == msg_b
    assert b"LemmaBountyIdentityBindingV1" in msg_a
    assert hashlib.sha256(msg_a).hexdigest()


def test_transaction_encoders_use_expected_selectors() -> None:
    commit_data = encode_commit_proof_call(12, "0x" + "ab" * 32)
    reveal_data = encode_reveal_proof_call(
        escrow_bounty_id=12,
        commitment_hash_hex="0x" + "ab" * 32,
        artifact_sha256=ARTIFACT_HASH,
        salt=SALT,
        payout_evm_address=PAYOUT,
        submitter_hotkey_pubkey=HOTKEY_PUBKEY,
    )

    assert commit_data.startswith("0xede854e6")
    assert reveal_data.startswith("0x18506722")
    assert len(commit_data) == 2 + 4 * 2 + 32 * 2 * 2
    assert len(reveal_data) == 2 + 4 * 2 + 32 * 2 * 6


def test_proof_artifact_sha256_hashes_file_bytes(tmp_path: Path) -> None:
    proof = tmp_path / "Submission.lean"
    proof.write_text("import Mathlib\n", encoding="utf-8")

    assert proof_artifact_sha256(proof) == hashlib.sha256(b"import Mathlib\n").hexdigest()


def test_registry_escrow_backed_requires_funding_confirmation() -> None:
    problem = {
        "id": "fc.test",
        "theorem_name": "test_theorem",
        "type_expr": "True",
        "split": "bounty",
        "lean_toolchain": "leanprover/lean4:v4.15.0",
        "mathlib_rev": "abc123",
        "imports": ["Mathlib"],
        "extra": {"informal_statement": "Prove True."},
    }
    base_row = {
        "id": "fc.test",
        "title": "Test bounty",
        "source": {"name": "Formal Conjectures"},
        "problem": problem,
        "escrow": {"chain_id": 945, "contract_address": CONTRACT, "bounty_id": 1},
    }

    draft = load_registry(
        b'{"schema_version":2,"bounties":['
        + json.dumps(base_row, sort_keys=True).encode()
        + b"]}",
    ).get("fc.test")
    funded = load_registry(
        b'{"schema_version":2,"bounties":['
        + json.dumps({**base_row, "escrow": {**base_row["escrow"], "funded": True}}, sort_keys=True).encode()
        + b"]}",
    ).get("fc.test")

    assert not draft.escrow_backed
    assert funded.escrow_backed
