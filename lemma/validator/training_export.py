"""Append proof-side training rows (JSONL) from validator epochs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from lemma.judge.base import RubricScore
from lemma.lean.proof_metrics import LeanProofMetrics
from lemma.protocol import LemmaChallenge

TrainingExportProfile = Literal["full", "summary", "reasoning_only"]


def round_summary_record(
    *,
    block: int,
    theorem_id: str,
    passed_uids: list[int] | set[int] | frozenset[int],
    export_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One round marker, including zero-pass rounds."""
    row: dict[str, Any] = {
        "schema_version": 2,
        "record_type": "round_summary",
        "block": block,
        "theorem_id": theorem_id,
        "passed_uids": sorted(int(uid) for uid in passed_uids),
    }
    if export_context:
        row["export_context"] = dict(export_context)
    return row


def training_record(
    *,
    block: int,
    theorem_id: str,
    uid: int,
    resp: LemmaChallenge,
    rubric: RubricScore | None = None,
    profile: TrainingExportProfile = "full",
    proof_metrics: LeanProofMetrics | None = None,
    coldkey: str | None = None,
    export_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One JSON-serializable row for dataset export.

    ``full`` (schema_version 1): proof, optional labels, optional proof metrics, and later ``pareto_weight`` —
    highest fidelity for offline analysis.

    ``summary`` (schema_version 2): identifiers and provenance only — omits proof text,
    labels, proof metrics, and incentive weights when appended (see ``append_epoch_jsonl``).
    """
    common = {
        "block": block,
        "theorem_id": theorem_id,
        "uid": uid,
        "export_profile": "summary" if profile == "reasoning_only" else profile,
        "model_card": resp.model_card,
    }
    if export_context:
        common["export_context"] = dict(export_context)
    if profile in ("summary", "reasoning_only"):
        return {
            "schema_version": 2,
            **common,
        }
    row = {
        "schema_version": 1,
        **common,
        "theorem_statement": resp.theorem_statement,
        "proof_script": resp.proof_script or "",
    }
    if rubric is not None:
        row["rubric"] = rubric.model_dump()
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
            out = dict(row)
            uid = out.get("uid")
            if include_pareto_weights and uid is not None:
                out["pareto_weight"] = float(weights_by_uid.get(int(uid), 0.0))
            f.write(json.dumps(out, ensure_ascii=False) + "\n")
        f.flush()
