"""Optional multipliers for easy/medium/hard catalog splits."""

from __future__ import annotations


def split_timeout_multiplier(split: str, easy: float, medium: float, hard: float) -> float:
    """Return the multiplier for ``split``; unknown splits use ``1.0``."""
    s = (split or "").strip().lower()
    if s == "easy":
        return float(easy)
    if s == "medium":
        return float(medium)
    if s == "hard":
        return float(hard)
    return 1.0
