"""Heuristic intrinsic score from Lean proof text (validator-local, deterministic)."""

from __future__ import annotations

import math
import re


def strip_lean_comments_for_intrinsic(src: str) -> str:
    """Best-effort removal of Lean comments and empty lines.

    Imperfect inside string literals, but removes the dominant comment-padding pattern for
    ``proof_intrinsic_score``. Innermost ``/- ... -/`` pairs are stripped repeatedly until stable.
    """
    out = src or ""
    while "/-" in out:
        new = re.sub(r"/-[\s\S]*?-/", "", out, count=1)
        if new == out:
            break
        out = new
    out = re.sub(r"--[^\n]*", "", out)
    return "\n".join(line for line in out.splitlines() if line.strip())


def proof_intrinsic_score(proof_script: str, *, strip_comments: bool = True) -> float:
    """Return a score in ``[0, 1]`` from proof length / structure proxies.

    This is not a measure of mathematical difficulty — only a coarse signal to reduce
    judge-only dominance when combined with ``LEMMA_SCORE_PROOF_WEIGHT``.
    """
    s = (proof_script or "").strip()
    if strip_comments:
        s = strip_lean_comments_for_intrinsic(s).strip()
    if not s:
        return 0.0
    n_chars = len(s)
    by_hits = len(re.findall(r"\bby\b", s))
    lines = s.count("\n") + 1
    len_norm = min(1.0, math.log1p(n_chars) / math.log1p(12_000.0))
    tact_norm = min(1.0, by_hits / 10.0)
    line_norm = min(1.0, lines / 48.0)
    raw = 0.5 * len_norm + 0.3 * tact_norm + 0.2 * line_norm
    return float(max(0.0, min(1.0, raw)))
