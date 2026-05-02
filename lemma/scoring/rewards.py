"""Combine objective pass with judge composite."""

from __future__ import annotations

from lemma.judge.base import RubricScore
from lemma.scoring.pareto import ScoredEntry
from lemma.scoring.tokens import count_tokens


def entry_from_scores(uid: int, rubric: RubricScore, trace: str, token_model: str = "gpt-4") -> ScoredEntry:
    toks = count_tokens(trace, model=token_model)
    return ScoredEntry(
        uid=uid,
        reasoning_score=rubric.composite,
        tokens=toks,
        composite=rubric.composite,
    )
