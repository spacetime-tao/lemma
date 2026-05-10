"""Pareto weighting."""

from lemma.scoring.pareto import ScoredEntry, pareto_weights


def test_pareto_prefers_lower_cost_at_same_score() -> None:
    a = ScoredEntry(uid=1, score=0.9, cost=100)
    b = ScoredEntry(uid=2, score=0.9, cost=50)
    w = pareto_weights([a, b])
    assert w[2] > w[1]


def test_pareto_normalize_sum() -> None:
    entries = [
        ScoredEntry(uid=0, score=1.0, cost=10),
        ScoredEntry(uid=1, score=0.5, cost=5),
    ]
    w = pareto_weights(entries)
    assert abs(sum(w.values()) - 1.0) < 1e-6
