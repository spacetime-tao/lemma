"""Pareto frontier over score vs optional proof-side cost."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class ScoredEntry:
    uid: int
    score: float
    cost: int
    #: Fingerprint of the normalized theorem/proof payload for offline analysis.
    submission_fp: str = ""


def _dominates(a: ScoredEntry, b: ScoredEntry) -> bool:
    """True iff ``a`` Pareto-dominates ``b`` (maximize score, minimize cost)."""
    better_or_eq_score = a.score >= b.score
    better_or_eq_cost = a.cost <= b.cost
    strictly_better = (a.score > b.score) or (a.cost < b.cost)
    return better_or_eq_score and better_or_eq_cost and strictly_better


def _pareto_frontier(pool: list[ScoredEntry]) -> list[ScoredEntry]:
    return [e for e in pool if not any(_dominates(o, e) for o in pool if o.uid != e.uid)]


def pareto_layers(entries: Iterable[ScoredEntry]) -> list[list[ScoredEntry]]:
    """Peel Pareto layers (non-dominated sets) until empty."""
    remaining = list(entries)
    layers: list[list[ScoredEntry]] = []
    while remaining:
        front = _pareto_frontier(remaining)
        if not front:
            break
        layers.append(front)
        rem_uids = {e.uid for e in front}
        remaining = [e for e in remaining if e.uid not in rem_uids]
    return layers


def pareto_weights(entries: list[ScoredEntry]) -> dict[int, float]:
    """
    Map miner UID -> normalized weight.

    Layer ``k`` receives discount ``0.5 ** k`` applied to ``score``.
    """
    if not entries:
        return {}
    layers = pareto_layers(entries)
    raw: dict[int, float] = {}
    for k, layer in enumerate(layers):
        discount = 0.5**k
        for e in layer:
            raw[e.uid] = max(e.score, 1e-9) * discount
    total = sum(raw.values())
    if total <= 0:
        return {uid: 1.0 / len(raw) for uid in raw}
    return {uid: v / total for uid, v in raw.items()}
