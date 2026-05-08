"""Parse rubric JSON from LLM output (strict, fail-closed)."""

from __future__ import annotations

import json
import re
from typing import Any

from lemma.judge.base import RubricScore

_EXPECTED_KEYS = frozenset({"coherence", "exploration", "clarity"})


def _strip_markdown_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*\n?", "", t)
        t = re.sub(r"\n?```\s*$", "", t)
    return t.strip()


def _extract_balanced_objects(text: str) -> list[str]:
    """Return substrings that look like top-level JSON objects (brace-balanced)."""
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        start = i
        depth = 0
        in_str = False
        esc = False
        quote = ""
        j = i
        found = False
        while j < n:
            ch = text[j]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == quote:
                    in_str = False
            else:
                if ch in "\"'":
                    in_str = True
                    quote = ch
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        out.append(text[start : j + 1])
                        i = j + 1
                        found = True
                        break
            j += 1
        if not found:
            i = start + 1
    return out


def _validate_rubric_dict(data: dict[str, Any]) -> RubricScore:
    if set(data.keys()) != _EXPECTED_KEYS:
        raise ValueError(
            f"judge JSON must have exactly keys {_EXPECTED_KEYS!r}, got {set(data.keys())!r}",
        )
    c = float(data["coherence"])
    e = float(data["exploration"])
    cl = float(data["clarity"])
    for name, v in (("coherence", c), ("exploration", e), ("clarity", cl)):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"judge dimension {name} out of range [0,1]: {v!r}")
    comp = (c + e + cl) / 3.0
    return RubricScore(coherence=c, exploration=e, clarity=cl, composite=comp)


def parse_rubric_json(text: str) -> RubricScore:
    """Parse exactly one rubric object. Rejects multiple JSON objects or extra keys."""
    raw = _strip_markdown_fence(text)
    if not raw:
        raise ValueError("judge returned empty response")

    candidates: list[dict[str, Any]] = []

    # 1) Whole string is JSON
    try:
        obj = json.loads(raw)
        if isinstance(obj, dict):
            candidates.append(obj)
    except json.JSONDecodeError:
        pass

    # 2) Balanced { ... } slices
    for frag in _extract_balanced_objects(raw):
        try:
            obj = json.loads(frag)
            if isinstance(obj, dict):
                candidates.append(obj)
        except json.JSONDecodeError:
            continue

    valid: list[RubricScore] = []
    seen: set[tuple[float, float, float]] = set()
    for obj in candidates:
        try:
            score = _validate_rubric_dict(obj)
        except ValueError as e:
            msg = str(e)
            if "exactly keys" in msg or "out of range" in msg:
                raise
            continue
        except (TypeError, KeyError):
            continue
        else:
            key = (score.coherence, score.exploration, score.clarity)
            if key not in seen:
                seen.add(key)
                valid.append(score)

    if len(valid) != 1:
        raise ValueError(
            f"judge output must contain exactly one valid rubric object; "
            f"found {len(valid)} candidate(s); raw_head={raw[:400]!r}",
        )
    return valid[0]
