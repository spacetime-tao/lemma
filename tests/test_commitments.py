from __future__ import annotations

from lemma.commitments import build_proof_commitment, commitment_payload_matches, decode_commitment_payload
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
