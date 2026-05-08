"""Parse rubric JSON from LLM output (strict, fail-closed)."""

from __future__ import annotations

import json
import re
from typing import Any

from lemma.judge.base import RubricScore

_EXPECTED_KEYS = frozenset({"coherence", "exploration", "clarity"})

# Prefer spans that open like JSON rubrics so preamble `{ ... }` (set notation, prose) does not
# steal brace-balancing from the real object.
_RUBRIC_KEY_OPEN = re.compile(r'\{\s*"(?:coherence|exploration|clarity)"\s*:')


def _strip_markdown_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z0-9]*\s*\n?", "", t)
        t = re.sub(r"\n?```\s*$", "", t)
    return t.strip()


def _balanced_object_at(text: str, start: int) -> str | None:
    """Return the brace-balanced `{...}` substring starting at ``start``, or None."""
    n = len(text)
    if start < 0 or start >= n or text[start] != "{":
        return None
    depth = 0
    in_str = False
    esc = False
    quote = ""
    j = start
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
                    return text[start : j + 1]
        j += 1
    return None


def _extract_balanced_objects(text: str) -> list[str]:
    """Return substrings that look like top-level JSON objects (brace-balanced)."""
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        span = _balanced_object_at(text, i)
        if span is not None:
            out.append(span)
            i += len(span)
        else:
            i += 1
    return out


def _anchored_rubric_json_spans(text: str) -> list[str]:
    """Brace-balanced spans that open like ``{\"coherence\"`` / ``{\"exploration\"`` / ``{\"clarity\"``.

    Reduces false positives when the model emits unrelated ``{ ... }`` before the rubric JSON.
    """
    spans: list[str] = []
    seen_start: set[int] = set()
    for m in _RUBRIC_KEY_OPEN.finditer(text):
        st = m.start()
        if st in seen_start:
            continue
        seen_start.add(st)
        span = _balanced_object_at(text, st)
        if span:
            spans.append(span)
    return spans


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

    # 2) Rubric-shaped openings first (robust when prose contains unrelated `{ ... }`).
    for frag in _anchored_rubric_json_spans(raw):
        try:
            obj = json.loads(frag)
            if isinstance(obj, dict):
                candidates.append(obj)
        except json.JSONDecodeError:
            continue

    # 3) Any balanced { ... } slices (legacy path; keys may appear in any order in fragment)
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
        except ValueError:
            # Wrong-shape dicts are skipped so a later rubric object can still win (prose + junk JSON).
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
