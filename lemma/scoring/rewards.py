"""Combine objective pass with judge composite."""

from __future__ import annotations

from lemma.judge.base import RubricScore
from lemma.scoring.dedup import submission_fingerprint
from lemma.scoring.pareto import ScoredEntry
from lemma.scoring.proof_intrinsic import proof_intrinsic_score
from lemma.scoring.tokens import count_tokens


def entry_from_scores(
    uid: int,
    rubric: RubricScore,
    trace: str,
    *,
    theorem_statement: str,
    proof_script: str,
    proof_weight: float,
    token_model: str = "gpt-4",
) -> ScoredEntry:
    """Blend intrinsic proof heuristic with judge rubric (``proof_weight`` in ``[0,1]``)."""
    w = max(0.0, min(1.0, float(proof_weight)))
    p_inst = proof_intrinsic_score(proof_script)
    combined = w * p_inst + (1.0 - w) * float(rubric.composite)
    toks = count_tokens(trace, model=token_model)
    fp = submission_fingerprint(theorem_statement, proof_script, trace)
    return ScoredEntry(
        uid=uid,
        reasoning_score=combined,
        tokens=toks,
        composite=combined,
        submission_fp=fp,
    )
