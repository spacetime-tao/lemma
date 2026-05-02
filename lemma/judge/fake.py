"""Deterministic judge for dry-runs and CI."""

from __future__ import annotations

from lemma.judge.base import RubricScore


class FakeJudge:
    async def score(self, theorem: str, trace: str, proof: str) -> RubricScore:
        del theorem, proof
        t = len(trace or "")
        base = 0.55 + min(0.35, t / 10_000.0)
        return RubricScore(
            coherence=base,
            exploration=base,
            clarity=base,
            composite=base,
        )
