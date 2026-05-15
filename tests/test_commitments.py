from __future__ import annotations

import json
from pathlib import Path

from lemma.commitments import (
    build_proof_commitment,
    canonical_json,
    commitment_payload_matches,
    decode_commitment_payload,
)
from lemma.problems.base import Problem


def _problem() -> Problem:
    return Problem(
        id="known/test/commit",
        theorem_name="target",
        type_expr="True",
        split="known_theorems",
        lean_toolchain="lt",
        mathlib_rev="mr",
        imports=("Mathlib",),
    )


def test_commitment_hash_is_canonical_and_stable() -> None:
    problem = _problem()
    first = build_proof_commitment(
        netuid=7,
        miner_hotkey="hotkey-a",
        manifest_sha256="m" * 64,
        problem=problem,
        proof_hash="p" * 64,
        nonce="secret",
    )
    second = build_proof_commitment(
        netuid=7,
        miner_hotkey="hotkey-a",
        manifest_sha256="m" * 64,
        problem=problem,
        proof_hash="p" * 64,
        nonce="secret",
    )

    assert first.payload_text == second.payload_text
    assert len(first.payload_text.encode()) <= 128
    assert first.commitment_hash == second.commitment_hash
    assert "proof_sha256" not in first.payload
    assert "nonce" not in first.payload


def test_commitment_v1_fixture_matches_python_builder() -> None:
    fixture = json.loads((Path(__file__).parent / "fixtures" / "commitment_v1.json").read_text(encoding="utf-8"))
    problem = Problem(
        id=fixture["problem"]["id"],
        theorem_name=fixture["problem"]["theorem_name"],
        type_expr=fixture["problem"]["type_expr"],
        split=fixture["problem"]["split"],
        lean_toolchain=fixture["problem"]["lean_toolchain"],
        mathlib_rev=fixture["problem"]["mathlib_rev"],
        imports=tuple(fixture["problem"]["imports"]),
    )
    commitment = build_proof_commitment(
        netuid=fixture["preimage"]["netuid"],
        miner_hotkey=fixture["preimage"]["miner_hotkey"],
        manifest_sha256=fixture["preimage"]["manifest_sha256"],
        problem=problem,
        proof_hash=fixture["preimage"]["proof_sha256"],
        nonce=fixture["preimage"]["nonce"],
    )

    assert problem.theorem_statement_sha256() == fixture["preimage"]["theorem_statement_sha256"]
    assert canonical_json(fixture["preimage"]) == fixture["canonical_json"]
    assert commitment.commitment_hash == fixture["commitment_hash"]
    assert commitment.payload_text == fixture["payload_text"]


def test_copied_commitment_fails_under_different_hotkey() -> None:
    problem = _problem()
    commitment = build_proof_commitment(
        netuid=7,
        miner_hotkey="hotkey-a",
        manifest_sha256="m" * 64,
        problem=problem,
        proof_hash="p" * 64,
        nonce="secret",
    )

    assert not commitment_payload_matches(
        commitment.payload_text,
        netuid=7,
        miner_hotkey="hotkey-b",
        manifest_sha256="m" * 64,
        problem=problem,
        proof_hash="p" * 64,
        nonce="secret",
        commitment_hash=commitment.commitment_hash,
    )


def test_proof_hash_alone_cannot_forge_commitment() -> None:
    problem = _problem()
    commitment = build_proof_commitment(
        netuid=7,
        miner_hotkey="hotkey-a",
        manifest_sha256="m" * 64,
        problem=problem,
        proof_hash="p" * 64,
        nonce="secret",
    )
    payload = decode_commitment_payload(commitment.payload_text)

    assert payload is not None
    assert "proof_sha256" not in payload
    assert "nonce" not in payload
    assert not commitment_payload_matches(
        commitment.payload_text,
        netuid=7,
        miner_hotkey="hotkey-a",
        manifest_sha256="m" * 64,
        problem=problem,
        proof_hash="p" * 64,
        nonce="wrong",
        commitment_hash=commitment.commitment_hash,
    )
