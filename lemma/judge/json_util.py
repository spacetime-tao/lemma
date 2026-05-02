"""Parse rubric JSON from LLM output."""

from __future__ import annotations

import json
import re

from lemma.judge.base import RubricScore


def parse_rubric_json(text: str) -> RubricScore:
    text = text.strip()
    m = re.search(r"\{[^}]+\}", text)
    if not m:
        raise ValueError(f"judge returned non-JSON: {text[:500]}")
    data = json.loads(m.group(0))
    c = float(data["coherence"])
    e = float(data["exploration"])
    cl = float(data["clarity"])
    comp = (c + e + cl) / 3.0
    return RubricScore(coherence=c, exploration=e, clarity=cl, composite=comp)
