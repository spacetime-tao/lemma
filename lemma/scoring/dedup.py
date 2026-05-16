"""Proof fingerprints and coldkey reward partitioning."""

from __future__ import annotations

import hashlib
import re
from collections import defaultdict
from collections.abc import Callable

from lemma.scoring.pareto import ScoredEntry
from lemma.scoring.proof_intrinsic import strip_lean_comments_for_intrinsic


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def submission_fingerprint(theorem_statement: str, proof_script: str) -> str:
    """Stable hash of a normalized proof payload."""
    parts = (
        _collapse_ws(theorem_statement),
        _collapse_ws(strip_lean_comments_for_intrinsic(proof_script)),
    )
    h = hashlib.sha256()
    for part in parts:
        h.update(part.encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()


def partition_same_coldkey_weights(
    weights: dict[int, float],
    uid_to_coldkey: Callable[[int], str],
) -> tuple[dict[int, float], int]:
    """Cap same-coldkey hotkeys to one allocation, then split it among them."""
    if not weights:
        return {}, 0

    groups: dict[str, list[int]] = defaultdict(list)
    for uid in weights:
        groups[uid_to_coldkey(uid)].append(uid)

    adjusted = {uid: max(0.0, weight) for uid, weight in weights.items()}
    partitioned = 0
    for uids in groups.values():
        if len(uids) < 2:
            continue
        group_total = sum(adjusted[uid] for uid in uids)
        group_cap = max(adjusted[uid] for uid in uids)
        if group_total <= 0.0 or group_cap >= group_total:
            continue
        scale = group_cap / group_total
        for uid in uids:
            adjusted[uid] *= scale
        partitioned += len(uids)

    total = sum(adjusted.values())
    if total <= 0.0:
        equal = 1.0 / len(adjusted)
        return {uid: equal for uid in adjusted}, partitioned
    return {uid: weight / total for uid, weight in adjusted.items()}, partitioned


def dedup_identical_submissions(
    entries: list[ScoredEntry],
    key_fn: Callable[[ScoredEntry], str],
) -> tuple[list[ScoredEntry], int]:
    """Offline replay helper: keep the highest ``score`` entry per identical key."""
    best: dict[str, ScoredEntry] = {}
    for e in entries:
        key = key_fn(e)
        cur = best.get(key)
        if cur is None or e.score > cur.score:
            best[key] = e
    kept = list(best.values())
    dropped = max(0, len(entries) - len(kept))
    return kept, dropped
