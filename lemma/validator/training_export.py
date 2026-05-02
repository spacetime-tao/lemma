"""Append PRM-style training rows (JSONL) from validator epochs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from lemma.judge.base import RubricScore
from lemma.protocol import LemmaChallenge
from lemma.reasoning.format import effective_reasoning_text


def training_record(
    *,
    block: int,
    theorem_id: str,
    uid: int,
    resp: LemmaChallenge,
    rubric: RubricScore,
) -> dict[str, Any]:
    """One JSON-serializable row for dataset export."""
    steps = resp.reasoning_steps
    return {
        "schema_version": 1,
        "block": block,
        "theorem_id": theorem_id,
        "uid": uid,
        "model_card": resp.model_card,
        "reasoning_steps": [s.model_dump() for s in steps] if steps else None,
        "reasoning_text": effective_reasoning_text(resp),
        "proof_script": resp.proof_script or "",
        "rubric": rubric.model_dump(),
    }


def append_epoch_jsonl(path: Path, rows: list[dict[str, Any]], weights_by_uid: dict[int, float]) -> None:
    """Append one JSON object per line; merge Pareto weights by uid."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            uid = int(row["uid"])
            out = dict(row)
            out["pareto_weight"] = float(weights_by_uid.get(uid, 0.0))
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
        f.flush()
