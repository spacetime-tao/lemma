"""Append PRM-style training rows (JSONL) from validator epochs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from lemma.judge.base import RubricScore
from lemma.lean.proof_metrics import LeanProofMetrics
from lemma.protocol import LemmaChallenge
from lemma.reasoning.format import effective_reasoning_text

TrainingExportProfile = Literal["full", "reasoning_only"]


def training_record(
    *,
    block: int,
    theorem_id: str,
    uid: int,
    resp: LemmaChallenge,
    rubric: RubricScore,
    profile: TrainingExportProfile = "full",
    proof_metrics: LeanProofMetrics | None = None,
    coldkey: str | None = None,
) -> dict[str, Any]:
    """One JSON-serializable row for dataset export.

    ``full`` (schema_version 1): proof, rubric, optional proof metrics, and later ``pareto_weight`` —
    highest fidelity for offline analysis; also the strongest labels for reverse-engineering the judge.

    ``reasoning_only`` (schema_version 2): reasoning trace + identifiers only — omits proof text, judge
    rubric, proof metrics, and incentive weights when appended (see ``append_epoch_jsonl``).
    """
    steps = resp.reasoning_steps
    common = {
        "block": block,
        "theorem_id": theorem_id,
        "uid": uid,
        "model_card": resp.model_card,
        "reasoning_steps": [s.model_dump() for s in steps] if steps else None,
        "reasoning_text": effective_reasoning_text(resp),
    }
    if profile == "reasoning_only":
        return {
            "schema_version": 2,
            "export_profile": "reasoning_only",
            **common,
        }
    row = {
        "schema_version": 1,
        **common,
        "proof_script": resp.proof_script or "",
        "rubric": rubric.model_dump(),
    }
    if coldkey:
        row["coldkey"] = coldkey
    if proof_metrics is not None:
        row["proof_metrics"] = proof_metrics.model_dump()
    return row


def append_epoch_jsonl(
    path: Path,
    rows: list[dict[str, Any]],
    weights_by_uid: dict[int, float],
    *,
    include_pareto_weights: bool = True,
) -> None:
    """Append one JSON object per line; optionally merge Pareto weights by uid (``full`` export only)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in rows:
            uid = int(row["uid"])
            out = dict(row)
            if include_pareto_weights:
                out["pareto_weight"] = float(weights_by_uid.get(uid, 0.0))
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
        f.flush()
