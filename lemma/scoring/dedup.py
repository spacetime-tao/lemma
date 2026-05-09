"""Anti-copy deduplication for scored miner entries."""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from lemma.scoring.pareto import ScoredEntry


def submission_fingerprint(theorem_statement: str, proof_script: str, trace_text: str) -> str:
    """Stable hash of miner-visible submission payload (per theorem)."""
    h = hashlib.sha256()
    for part in (theorem_statement, proof_script, trace_text):
        h.update((part or "").encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()


def dedup_identical_submissions(
    entries: list[ScoredEntry],
    key_fn: Callable[[ScoredEntry], str],
) -> tuple[list[ScoredEntry], int]:
    """Keep the highest ``reasoning_score`` entry per identical key; return (kept, dropped_count)."""
    return _dedup_by_key(entries, key_fn)


def dedup_coldkeys(
    entries: list[ScoredEntry],
    uid_to_coldkey: Callable[[int], str],
) -> tuple[list[ScoredEntry], int]:
    """Keep the highest ``reasoning_score`` entry per coldkey string."""
    return _dedup_by_key(entries, lambda e: uid_to_coldkey(e.uid))


def _dedup_by_key(
    entries: list[ScoredEntry],
    key_fn: Callable[[ScoredEntry], str],
) -> tuple[list[ScoredEntry], int]:
    """Keep the highest ``reasoning_score`` entry per key."""
    best: dict[str, ScoredEntry] = {}
    for e in entries:
        key = key_fn(e)
        cur = best.get(key)
        if cur is None or e.reasoning_score > cur.reasoning_score:
            best[key] = e
    kept = list(best.values())
    dropped = max(0, len(entries) - len(kept))
    return kept, dropped
