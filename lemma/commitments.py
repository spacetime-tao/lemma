"""Proof commitment helpers for copy-resistant reveal."""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any

from lemma.problems.base import Problem

COMMITMENT_SCHEMA = "lemma_proof_commitment_v1"
COMMITMENT_PREFIX = "lemma:v1:"


@dataclass(frozen=True)
class ProofCommitment:
    payload: dict[str, Any]
    payload_text: str
    commitment_hash: str


def new_nonce() -> str:
    return secrets.token_hex(32)


def proof_sha256(proof_script: str) -> str:
    return hashlib.sha256(proof_script.encode("utf-8")).hexdigest()


def build_proof_commitment(
    *,
    netuid: int,
    miner_hotkey: str,
    manifest_sha256: str,
    problem: Problem,
    proof_hash: str,
    nonce: str,
) -> ProofCommitment:
    commitment_hash = _commitment_hash(
        {
            "schema": COMMITMENT_SCHEMA,
            "netuid": int(netuid),
            "miner_hotkey": miner_hotkey,
            "manifest_sha256": manifest_sha256,
            "target_id": problem.id,
            "theorem_statement_sha256": problem.theorem_statement_sha256(),
            "proof_sha256": proof_hash,
            "nonce": nonce,
        },
    )
    payload = {"schema": COMMITMENT_SCHEMA, "commitment_hash": commitment_hash}
    return ProofCommitment(
        payload=payload,
        payload_text=f"{COMMITMENT_PREFIX}{commitment_hash}",
        commitment_hash=commitment_hash,
    )


def canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def decode_commitment_payload(text: str) -> dict[str, Any] | None:
    if text.startswith(COMMITMENT_PREFIX):
        commitment_hash = text.removeprefix(COMMITMENT_PREFIX)
        if len(commitment_hash) == 64:
            return {"schema": COMMITMENT_SCHEMA, "commitment_hash": commitment_hash}
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    if data.get("schema") != COMMITMENT_SCHEMA:
        return None
    return data


def commitment_payload_matches(
    text: str,
    *,
    netuid: int,
    miner_hotkey: str,
    manifest_sha256: str,
    problem: Problem,
    proof_hash: str,
    nonce: str,
    commitment_hash: str,
) -> bool:
    expected = build_proof_commitment(
        netuid=netuid,
        miner_hotkey=miner_hotkey,
        manifest_sha256=manifest_sha256,
        problem=problem,
        proof_hash=proof_hash,
        nonce=nonce,
    )
    data = decode_commitment_payload(text)
    return (
        data is not None
        and data.get("commitment_hash") == expected.commitment_hash
        and commitment_hash == expected.commitment_hash
    )


def _commitment_hash(preimage: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(preimage).encode("utf-8")).hexdigest()
