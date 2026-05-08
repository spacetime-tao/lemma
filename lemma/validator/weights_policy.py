"""Normalize epoch weights and handle empty-score rounds."""

from __future__ import annotations

from typing import Literal


def build_full_weights(
    n: int,
    weights_by_uid: dict[int, float],
    *,
    empty_policy: Literal["skip", "uniform"],
    exclude_uid: int | None = None,
) -> tuple[list[float], bool]:
    """
    Build length-``n`` weight vector.

    Returns ``(weights, skip_chain_write)``. When ``skip_chain_write`` is True the caller
    should not invoke ``set_weights`` (used when there are no scored miners and policy is skip).
    """
    if weights_by_uid:
        full = [0.0] * n
        for uid, w in weights_by_uid.items():
            if isinstance(uid, int) and 0 <= uid < n:
                full[uid] = w
        total = sum(full)
        if total > 0:
            full = [w / total for w in full]
        return full, False

    if n <= 0:
        return [], True

    if empty_policy == "uniform":
        if exclude_uid is not None and 0 <= exclude_uid < n and n > 1:
            denom = max(1, n - 1)
            u = 1.0 / denom
            full = [0.0] * n
            for i in range(n):
                if i != exclude_uid:
                    full[i] = u
            return full, False
        u = 1.0 / n
        return [u] * n, False

    return [0.0] * n, True
