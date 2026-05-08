"""Pareto frontier over reasoning quality vs trace length."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class ScoredEntry:
    uid: int
    reasoning_score: float
    tokens: int
    composite: float
    #: Fingerprint of (theorem, proof, trace) for identical-output dedup (optional).
    submission_fp: str = ""


def _dominates(a: ScoredEntry, b: ScoredEntry) -> bool:
    """True iff ``a`` Pareto-dominates ``b`` (maximize score, minimize tokens)."""
    better_or_eq_score = a.reasoning_score >= b.reasoning_score
    better_or_eq_tokens = a.tokens <= b.tokens
    strictly_better = (a.reasoning_score > b.reasoning_score) or (a.tokens < b.tokens)
    return better_or_eq_score and better_or_eq_tokens and strictly_better


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

    Layer ``k`` receives discount ``0.5 ** k`` applied to ``composite``.
    """
    if not entries:
        return {}
    layers = pareto_layers(entries)
    raw: dict[int, float] = {}
    for k, layer in enumerate(layers):
        discount = 0.5**k
        for e in layer:
            raw[e.uid] = max(e.composite, 1e-9) * discount
    total = sum(raw.values())
    if total <= 0:
        return {uid: 1.0 / len(raw) for uid in raw}
    return {uid: v / total for uid, v in raw.items()}
