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

MIN_DECISION_SUCCESSFUL_ROWS = 50
MIN_DECISION_THEOREMS = 5
MIN_DECISION_UIDS = 5


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
    proof_metric_delimiters: int | None
    proof_metric_max_depth: int | None
    probe_exit_code: int


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
    ok_rows = [r for r in rows if r.probe_exit_code == 0]
    failed_rows = len(rows) - len(ok_rows)
    verdict, reasons = metric_gate(rows)
    data_blockers, data_warnings = decision_data_findings(ok_rows, failed_rows=failed_rows)
    judged_rows = [r for r in ok_rows if r.judge_composite is not None]
    lines = [
        "Proof metrics export analysis",
        f"rows_total={report.total_rows}",
        f"rows_with_proof_metrics={len(rows)}",
        f"rows_with_successful_proof_metrics={len(ok_rows)}",
        f"rows_with_failed_proof_metrics={failed_rows}",
        f"invalid_json_lines={report.invalid_json_lines}",
        "decision_data="
        f"successful_rows={len(ok_rows)} "
        f"unique_theorems={_unique_theorem_count(ok_rows)} "
        f"unique_uids={_unique_uid_count(ok_rows)} "
        f"judged_rows={len(judged_rows)}",
        "decision_data_blockers=" + (",".join(data_blockers) if data_blockers else "none"),
        "decision_data_warnings=" + (",".join(data_warnings) if data_warnings else "none"),
        f"gate_verdict={verdict}",
        "gate_reasons=" + (",".join(reasons) if reasons else "none"),
    ]
    if not rows:
        lines.append("No rows with proof_metrics found.")
        return "\n".join(lines)
    if not ok_rows:
        lines.append("No successful proof_metrics found.")
        return "\n".join(lines)

    bytes_v = [r.proof_metric_bytes for r in ok_rows]
    lines_v = [r.proof_metric_lines for r in ok_rows]
    delimiter_rows = [r for r in ok_rows if r.proof_metric_delimiters is not None]
    delimiters_v = [r.proof_metric_delimiters for r in delimiter_rows]
    depth_v = [r.proof_metric_max_depth for r in ok_rows if r.proof_metric_max_depth is not None]
    proof_len_v = [r.proof_len for r in ok_rows]
    intrinsic_v = [r.proof_intrinsic for r in ok_rows]
    judged = [(r.proof_metric_bytes, r.judge_composite) for r in ok_rows if r.judge_composite is not None]
    judged_delimiters = [
        (r.proof_metric_delimiters, r.judge_composite)
        for r in ok_rows
        if r.proof_metric_delimiters is not None and r.judge_composite is not None
    ]

    lines.extend(
        [
            _stats_line("metric_bytes", bytes_v),
            _stats_line("metric_lines", lines_v),
            _stats_line("metric_delimiters", delimiters_v) if delimiters_v else "metric_delimiters: n=0",
            _stats_line("metric_max_depth", depth_v) if depth_v else "metric_max_depth: n=0",
            _stats_line("proof_len_chars", proof_len_v),
            f"corr(metric_bytes, proof_len_chars)={_format_corr(_pearson(bytes_v, proof_len_v))}",
            f"corr(metric_bytes, proof_intrinsic)={_format_corr(_pearson(bytes_v, intrinsic_v))}",
            "corr(metric_delimiters, proof_len_chars)="
            + _format_corr(_pearson(delimiters_v, [r.proof_len for r in delimiter_rows]) if delimiters_v else None),
            "corr(metric_delimiters, proof_intrinsic)="
            + _format_corr(
                _pearson(delimiters_v, [r.proof_intrinsic for r in delimiter_rows]) if delimiters_v else None,
            ),
            "corr(metric_bytes, judge_composite)="
            + _format_corr(_pearson([x for x, _ in judged], [y for _, y in judged]) if judged else None),
            "corr(metric_delimiters, judge_composite)="
            + _format_corr(
                _pearson([x for x, _ in judged_delimiters], [y for _, y in judged_delimiters])
                if judged_delimiters
                else None,
            ),
        ],
    )

    outliers = padding_outliers(ok_rows, limit=outlier_limit)
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

    candidates = low_judge_high_metric_candidates(ok_rows, limit=outlier_limit)
    if candidates:
        lines.append("low_judge_high_metric_candidates:")
        for r in candidates:
            lines.append(
                f"  line={r.line_no} theorem={r.theorem_id} uid={r.uid} "
                f"judge={r.judge_composite:.4f} metric_bytes={r.proof_metric_bytes} "
                f"proof_len={r.proof_len} intrinsic={r.proof_intrinsic:.4f}",
            )
    else:
        lines.append("low_judge_high_metric_candidates: none")
    return "\n".join(lines)


def padding_outliers(rows: list[MetricRow], *, limit: int) -> list[MetricRow]:
    ok_rows = [r for r in rows if r.probe_exit_code == 0 and r.proof_len > r.proof_metric_bytes]
    return sorted(ok_rows, key=lambda r: (r.proof_len - r.proof_metric_bytes, r.proof_len), reverse=True)[:limit]


def low_judge_high_metric_candidates(rows: list[MetricRow], *, limit: int, max_judge: float = 0.5) -> list[MetricRow]:
    ok_rows = [r for r in rows if r.probe_exit_code == 0]
    if not ok_rows:
        return []
    metric_floor = statistics.median(r.proof_metric_bytes for r in ok_rows)
    candidates = [
        r
        for r in ok_rows
        if r.judge_composite is not None and r.judge_composite <= max_judge and r.proof_metric_bytes >= metric_floor
    ]
    return sorted(candidates, key=lambda r: (r.proof_metric_bytes, r.proof_intrinsic, r.proof_len), reverse=True)[
        :limit
    ]


def decision_data_findings(ok_rows: list[MetricRow], *, failed_rows: int) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    if len(ok_rows) < MIN_DECISION_SUCCESSFUL_ROWS:
        blockers.append(f"fewer_than_{MIN_DECISION_SUCCESSFUL_ROWS}_successful_rows")
    if _unique_theorem_count(ok_rows) < MIN_DECISION_THEOREMS:
        blockers.append(f"fewer_than_{MIN_DECISION_THEOREMS}_theorems")
    if _unique_uid_count(ok_rows) < MIN_DECISION_UIDS:
        blockers.append(f"fewer_than_{MIN_DECISION_UIDS}_uids")

    judged = sum(1 for r in ok_rows if r.judge_composite is not None)
    if ok_rows and judged == 0:
        blockers.append("no_judge_composite_rows")
    elif judged < len(ok_rows):
        warnings.append("partial_judge_composite_rows")
    if failed_rows:
        warnings.append("failed_proof_metric_probes")
    return blockers, warnings


def metric_gate(rows: list[MetricRow]) -> tuple[str, list[str]]:
    ok_rows = [r for r in rows if r.probe_exit_code == 0]
    if not rows:
        return "insufficient_data", ["no_proof_metrics"]
    if not ok_rows:
        return "insufficient_data", ["no_successful_proof_metrics"]

    reasons: list[str] = []
    if len(ok_rows) < len(rows):
        reasons.append("failed_proof_metric_probes")
    if padding_outliers(ok_rows, limit=1):
        reasons.append("padding_outliers")
    if low_judge_high_metric_candidates(ok_rows, limit=1):
        reasons.append("low_judge_high_metric_candidates")
    if reasons:
        return "research_only", reasons
    return "manual_review_required", []


def _unique_theorem_count(rows: list[MetricRow]) -> int:
    return len({r.theorem_id for r in rows if r.theorem_id})


def _unique_uid_count(rows: list[MetricRow]) -> int:
    return len({r.uid for r in rows if r.uid is not None})


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
    metric_delimiters = _as_int(metrics.get("proof_declaration_delimiters"))
    metric_max_depth = _as_int(metrics.get("proof_declaration_max_depth"))
    proof = obj.get("proof_script") if isinstance(obj.get("proof_script"), str) else ""
    rubric = obj.get("rubric")
    judge = _as_float(rubric.get("composite")) if isinstance(rubric, dict) else None
    uid = _as_int(obj.get("uid"))
    exit_code = _as_int(metrics.get("probe_exit_code"))
    return MetricRow(
        line_no=line_no,
        theorem_id=str(obj.get("theorem_id") or ""),
        uid=uid,
        proof_len=len(proof),
        proof_intrinsic=proof_intrinsic_score(proof),
        judge_composite=judge,
        proof_metric_bytes=metric_bytes,
        proof_metric_lines=metric_lines,
        proof_metric_delimiters=metric_delimiters,
        proof_metric_max_depth=metric_max_depth,
        probe_exit_code=exit_code if exit_code is not None else 0,
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
