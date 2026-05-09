"""Pareto weighting."""

from lemma.scoring.pareto import ScoredEntry, pareto_weights


def test_pareto_prefers_shorter_trace_at_same_score() -> None:
    a = ScoredEntry(uid=1, reasoning_score=0.9, tokens=100)
    b = ScoredEntry(uid=2, reasoning_score=0.9, tokens=50)
    w = pareto_weights([a, b])
    assert w[2] > w[1]


def test_pareto_normalize_sum() -> None:
    entries = [
        ScoredEntry(uid=0, reasoning_score=1.0, tokens=10),
        ScoredEntry(uid=1, reasoning_score=0.5, tokens=5),
    ]
    w = pareto_weights(entries)
    assert abs(sum(w.values()) - 1.0) < 1e-6
