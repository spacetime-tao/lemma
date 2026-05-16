"""Reward assembly for proof-only verified submissions."""

from lemma.scoring.dedup import submission_fingerprint
from lemma.scoring.rewards import entry_from_verified_proof


def test_entry_from_verified_proof_scores_verified_proof() -> None:
    theorem = "theorem t : True := by sorry"
    proof = "theorem t : True := by trivial"

    entry = entry_from_verified_proof(
        7,
        theorem_statement=theorem,
        proof_script=proof,
    )

    assert entry.uid == 7
    assert entry.score == 1.0
    assert entry.cost == 0
    assert entry.submission_fp == submission_fingerprint(theorem, proof)


def test_entry_from_verified_proof_uses_normalized_proof_fingerprint() -> None:
    theorem = "theorem t : True := by sorry"
    a = entry_from_verified_proof(
        1,
        theorem_statement=theorem,
        proof_script="theorem t : True := by\n  trivial\n",
    )
    b = entry_from_verified_proof(
        1,
        theorem_statement=theorem,
        proof_script="-- padding\n\ntheorem t : True := by trivial\n",
    )

    assert a.submission_fp == b.submission_fp
