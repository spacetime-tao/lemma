"""Trace length proxy for Pareto efficiency."""

from __future__ import annotations


def count_tokens(text: str) -> int:
    """Deterministic monotone length proxy for the Pareto trace axis."""
    return len(text or "")
