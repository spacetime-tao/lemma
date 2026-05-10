"""Assemble live reward entries from Lean-verified proofs."""

from __future__ import annotations

from lemma.scoring.dedup import submission_fingerprint
from lemma.scoring.pareto import ScoredEntry


def entry_from_verified_proof(
    uid: int,
    *,
    theorem_statement: str,
    proof_script: str,
) -> ScoredEntry:
    """Return one binary reward entry for a proof that already passed Lean."""
    fp = submission_fingerprint(theorem_statement, proof_script)
    return ScoredEntry(
        uid=uid,
        score=1.0,
        cost=0,
        submission_fp=fp,
    )
