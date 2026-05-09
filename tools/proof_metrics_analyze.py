"""Analyze compare-only proof metrics from validator training exports."""

from __future__ import annotations

import argparse
import json
import os
import statistics
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lemma.scoring.proof_intrinsic import proof_intrinsic_score


@dataclass(frozen=True)
class MetricRow:
    line_no: int
    theorem_id: str
    uid: int | None
    proof_len: int
    proof_intrinsic: float
    judge_composite: float | None
    proof_metric_bytes: int
    proof_metric_lines: int


@dataclass(frozen=True)
class MetricsReport:
    total_rows: int
    invalid_json_lines: int
    metric_rows: list[MetricRow]


def load_report(path: Path) -> MetricsReport:
    total = 0
    invalid = 0
    rows: list[MetricRow] = []
    with path.open(encoding="utf-8") as f:
        for line_no, raw in enumerate(f, start=1):
            if not raw.strip():
                continue
            total += 1
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                invalid += 1
                continue
            metric = _metric_row(obj, line_no)
            if metric is not None:
                rows.append(metric)
    return MetricsReport(total_rows=total, invalid_json_lines=invalid, metric_rows=rows)


def render_report(report: MetricsReport, *, outlier_limit: int = 8) -> str:
    rows = report.metric_rows
    lines = [
        "Proof metrics export analysis",
        f"rows_total={report.total_rows}",
        f"rows_with_proof_metrics={len(rows)}",
        f"invalid_json_lines={report.invalid_json_lines}",
    ]
    if not rows:
        lines.append("No rows with proof_metrics found.")
        return "\n".join(lines)

    bytes_v = [r.proof_metric_bytes for r in rows]
    lines_v = [r.proof_metric_lines for r in rows]
    proof_len_v = [r.proof_len for r in rows]
    intrinsic_v = [r.proof_intrinsic for r in rows]
    judged = [(r.proof_metric_bytes, r.judge_composite) for r in rows if r.judge_composite is not None]

    lines.extend(
        [
            _stats_line("metric_bytes", bytes_v),
            _stats_line("metric_lines", lines_v),
            _stats_line("proof_len_chars", proof_len_v),
            f"corr(metric_bytes, proof_len_chars)={_format_corr(_pearson(bytes_v, proof_len_v))}",
            f"corr(metric_bytes, proof_intrinsic)={_format_corr(_pearson(bytes_v, intrinsic_v))}",
            "corr(metric_bytes, judge_composite)="
            + _format_corr(_pearson([x for x, _ in judged], [y for _, y in judged]) if judged else None),
        ],
    )

    outliers = padding_outliers(rows, limit=outlier_limit)
    if outliers:
        lines.append("padding_outliers_by_proof_len_minus_metric_bytes:")
        for r in outliers:
            gap = r.proof_len - r.proof_metric_bytes
            lines.append(
                f"  line={r.line_no} theorem={r.theorem_id} uid={r.uid} "
                f"gap={gap} proof_len={r.proof_len} metric_bytes={r.proof_metric_bytes} "
                f"intrinsic={r.proof_intrinsic:.4f}",
            )
    else:
        lines.append("padding_outliers_by_proof_len_minus_metric_bytes: none")
    return "\n".join(lines)


def padding_outliers(rows: list[MetricRow], *, limit: int) -> list[MetricRow]:
    return sorted(rows, key=lambda r: (r.proof_len - r.proof_metric_bytes, r.proof_len), reverse=True)[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "jsonl",
        nargs="?",
        type=Path,
        help="Training export JSONL. Defaults to LEMMA_TRAINING_EXPORT_JSONL.",
    )
    parser.add_argument("--outliers", type=int, default=8, help="Number of padding-looking rows to print.")
    args = parser.parse_args(argv)

    path = args.jsonl or _env_export_path()
    if path is None:
        parser.error("pass a JSONL path or set LEMMA_TRAINING_EXPORT_JSONL")
    if not path.is_file():
        parser.error(f"not a file: {path}")

    print(render_report(load_report(path), outlier_limit=max(0, int(args.outliers))))
    return 0


def _env_export_path() -> Path | None:
    raw = os.environ.get("LEMMA_TRAINING_EXPORT_JSONL", "").strip()
    return Path(raw).expanduser() if raw else None


def _metric_row(obj: Any, line_no: int) -> MetricRow | None:
    if not isinstance(obj, dict):
        return None
    metrics = obj.get("proof_metrics")
    if not isinstance(metrics, dict):
        return None
    metric_bytes = _as_int(metrics.get("proof_declaration_bytes"))
    metric_lines = _as_int(metrics.get("proof_declaration_lines"))
    if metric_bytes is None or metric_lines is None:
        return None
    proof = obj.get("proof_script") if isinstance(obj.get("proof_script"), str) else ""
    rubric = obj.get("rubric")
    judge = _as_float(rubric.get("composite")) if isinstance(rubric, dict) else None
    uid = _as_int(obj.get("uid"))
    return MetricRow(
        line_no=line_no,
        theorem_id=str(obj.get("theorem_id") or ""),
        uid=uid,
        proof_len=len(proof),
        proof_intrinsic=proof_intrinsic_score(proof),
        judge_composite=judge,
        proof_metric_bytes=metric_bytes,
        proof_metric_lines=metric_lines,
    )


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _stats_line(name: str, values: list[int]) -> str:
    if not values:
        return f"{name}: n=0"
    return (
        f"{name}: n={len(values)} min={min(values)} median={statistics.median(values):.1f} "
        f"mean={statistics.mean(values):.1f} max={max(values)}"
    )


def _pearson(xs: list[float | int], ys: list[float | int]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mx = statistics.mean(xs)
    my = statistics.mean(ys)
    dx = [float(x) - mx for x in xs]
    dy = [float(y) - my for y in ys]
    denom_x = sum(x * x for x in dx)
    denom_y = sum(y * y for y in dy)
    if denom_x <= 0.0 or denom_y <= 0.0:
        return None
    return sum(x * y for x, y in zip(dx, dy, strict=True)) / ((denom_x * denom_y) ** 0.5)


def _format_corr(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


if __name__ == "__main__":
    raise SystemExit(main())
