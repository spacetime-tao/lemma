"""Offline proof-metrics export analyzer."""

import json
from pathlib import Path

from tools.proof_metrics_analyze import (
    decision_ready,
    load_report,
    low_judge_high_metric_candidates,
    main,
    metric_gate,
    padding_outliers,
    render_report,
)

FIXTURE = Path(__file__).parent / "fixtures" / "proof_metrics_validation.jsonl"


def test_load_report_summarizes_metric_rows(tmp_path) -> None:
    path = tmp_path / "train.jsonl"
    rows = [
        {
            "theorem_id": "a",
            "uid": 1,
            "proof_script": "theorem a : True := by trivial\n",
            "rubric": {"composite": 0.8},
            "proof_metrics": {
                "proof_declaration_bytes": 50,
                "proof_declaration_lines": 3,
                "probe_exit_code": 0,
            },
        },
        {
            "theorem_id": "failed-probe",
            "uid": 4,
            "proof_script": "theorem f : True := by trivial\n" + "-- padding\n" * 200,
            "rubric": {"composite": 0.6},
            "proof_metrics": {
                "proof_declaration_bytes": 20,
                "proof_declaration_lines": 1,
                "probe_exit_code": 1,
            },
        },
        {"theorem_id": "reasoning-only", "uid": 2},
        {
            "theorem_id": "padded",
            "uid": 3,
            "proof_script": "theorem p : True := by trivial\n" + "-- padding\n" * 100,
            "rubric": {"composite": 0.3},
            "proof_metrics": {
                "proof_declaration_bytes": 40,
                "proof_declaration_lines": 2,
                "probe_exit_code": 0,
            },
        },
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n{bad json\n", encoding="utf-8")

    report = load_report(path)
    assert report.total_rows == 5
    assert report.invalid_json_lines == 1
    assert len(report.metric_rows) == 3

    outliers = padding_outliers(report.metric_rows, limit=1)
    assert outliers[0].theorem_id == "padded"

    rendered = render_report(report)
    assert "rows_with_proof_metrics=3" in rendered
    assert "rows_with_successful_proof_metrics=2" in rendered
    assert "rows_with_failed_proof_metrics=1" in rendered
    assert (
        "decision_data=successful_rows=2 unique_theorems=2 unique_uids=2 "
        "judged_rows=2 comparison_theorems=0"
    ) in rendered
    assert (
        "decision_data_blockers="
        "fewer_than_50_successful_rows,fewer_than_5_theorems,fewer_than_5_uids,"
        "fewer_than_3_judged_theorems_with_2_rows_and_2_uids"
    ) in rendered
    assert "decision_data_warnings=failed_proof_metric_probes" in rendered
    assert "gate_verdict=research_only" in rendered
    assert "failed_proof_metric_probes" in rendered
    assert "padding_outliers" in rendered
    assert "metric_delimiters: n=0" in rendered
    assert "metric_max_depth: n=0" in rendered
    assert "corr(metric_bytes, proof_len_chars)=" in rendered
    assert "corr(metric_delimiters, proof_len_chars)=n/a" in rendered
    assert "corr(metric_delimiters, proof_intrinsic)=n/a" in rendered
    assert "within_theorem_comparisons=theorems=0 rows=0" in rendered
    assert "corr_within_theorem(metric_bytes, judge_composite)=n/a" in rendered
    assert "padding_outliers_by_proof_len_minus_metric_bytes:" in rendered
    assert "low_judge_high_metric_candidates:" in rendered
    assert "theorem=padded" in rendered
    assert "theorem=failed-probe" not in rendered


def test_render_report_handles_only_failed_probe_rows(tmp_path) -> None:
    path = tmp_path / "failed.jsonl"
    path.write_text(
        json.dumps(
            {
                "theorem_id": "failed",
                "uid": 1,
                "proof_script": "theorem f : True := by trivial\n",
                "proof_metrics": {
                    "proof_declaration_bytes": 0,
                    "proof_declaration_lines": 0,
                    "probe_exit_code": 127,
                },
            },
        )
        + "\n",
        encoding="utf-8",
    )

    rendered = render_report(load_report(path))
    assert "rows_with_proof_metrics=1" in rendered
    assert "rows_with_successful_proof_metrics=0" in rendered
    assert "rows_with_failed_proof_metrics=1" in rendered
    assert (
        "decision_data=successful_rows=0 unique_theorems=0 unique_uids=0 "
        "judged_rows=0 comparison_theorems=0"
    ) in rendered
    assert (
        "decision_data_blockers="
        "fewer_than_50_successful_rows,fewer_than_5_theorems,fewer_than_5_uids"
    ) in rendered
    assert "decision_data_warnings=failed_proof_metric_probes" in rendered
    assert "gate_verdict=insufficient_data" in rendered
    assert "gate_reasons=no_successful_proof_metrics" in rendered
    assert "No successful proof_metrics found." in rendered
    assert padding_outliers(load_report(path).metric_rows, limit=1) == []


def test_main_uses_env_path(tmp_path, monkeypatch, capsys) -> None:
    path = tmp_path / "train.jsonl"
    path.write_text(
        json.dumps(
            {
                "theorem_id": "a",
                "uid": 1,
                "proof_script": "theorem a : True := by trivial\n",
                "proof_metrics": {
                    "proof_declaration_bytes": 50,
                    "proof_declaration_lines": 3,
                    "probe_exit_code": 0,
                },
            },
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LEMMA_TRAINING_EXPORT_JSONL", str(path))

    assert main(["--outliers", "0"]) == 0
    rendered = capsys.readouterr().out
    assert "rows_with_proof_metrics=1" in rendered
    assert (
        "decision_data=successful_rows=1 unique_theorems=1 unique_uids=1 "
        "judged_rows=0 comparison_theorems=0"
    ) in rendered
    assert "no_judge_composite_rows" in rendered
    assert "gate_verdict=manual_review_required" in rendered
    assert "gate_reasons=none" in rendered


def test_validation_fixture_separates_padding_from_failed_probes() -> None:
    report = load_report(FIXTURE)

    assert report.total_rows == 7
    assert report.invalid_json_lines == 0
    assert len(report.metric_rows) == 7

    rendered = render_report(report, outlier_limit=6)
    assert "rows_with_successful_proof_metrics=6" in rendered
    assert "rows_with_failed_proof_metrics=1" in rendered
    assert (
        "decision_data=successful_rows=6 unique_theorems=6 unique_uids=6 "
        "judged_rows=6 comparison_theorems=0"
    ) in rendered
    assert (
        "decision_data_blockers=fewer_than_50_successful_rows,"
        "fewer_than_3_judged_theorems_with_2_rows_and_2_uids"
    ) in rendered
    assert "decision_data_warnings=failed_proof_metric_probes" in rendered
    assert "decision_ready=no" in rendered
    assert "gate_verdict=research_only" in rendered
    assert "gate_reasons=failed_proof_metric_probes,padding_outliers,low_judge_high_metric_candidates" in rendered
    assert "metric_delimiters: n=6" in rendered
    assert "metric_max_depth: n=6" in rendered
    assert "corr(metric_delimiters, proof_len_chars)=" in rendered
    assert "corr(metric_delimiters, proof_intrinsic)=" in rendered
    assert "corr(metric_delimiters, judge_composite)=" in rendered
    assert "within_theorem_comparisons=theorems=0 rows=0" in rendered
    assert "theorem=comment-padding" in rendered
    assert "theorem=string-padding" in rendered
    assert "theorem=unused-have-padding" in rendered
    assert "theorem=long-name-padding" in rendered
    assert "theorem=failed-probe-padding" not in rendered
    assert "theorem=honest-short" not in rendered
    assert "theorem=honest-structured" not in rendered

    outlier_ids = [r.theorem_id for r in padding_outliers(report.metric_rows, limit=6)]
    assert outlier_ids == ["comment-padding"]
    assert "failed-probe-padding" not in outlier_ids

    risk_ids = [r.theorem_id for r in low_judge_high_metric_candidates(report.metric_rows, limit=6)]
    assert risk_ids == ["unused-have-padding", "long-name-padding", "string-padding"]
    assert "failed-probe-padding" not in risk_ids

    verdict, reasons = metric_gate(report.metric_rows)
    assert verdict == "research_only"
    assert reasons == ["failed_proof_metric_probes", "padding_outliers", "low_judge_high_metric_candidates"]
    assert decision_ready(report.metric_rows) is False


def test_require_decision_ready_returns_nonzero_for_blocked_export(tmp_path, capsys) -> None:
    path = tmp_path / "blocked.jsonl"
    path.write_text(
        json.dumps(
            {
                "theorem_id": "a",
                "uid": 1,
                "proof_script": "theorem a : True := by trivial\n",
                "rubric": {"composite": 0.9},
                "proof_metrics": {
                    "proof_declaration_bytes": 100,
                    "proof_declaration_lines": 5,
                    "proof_declaration_delimiters": 8,
                    "proof_declaration_max_depth": 3,
                    "probe_exit_code": 0,
                },
            },
        )
        + "\n",
        encoding="utf-8",
    )

    assert main([str(path), "--require-decision-ready"]) == 2
    assert "decision_ready=no" in capsys.readouterr().out


def test_require_decision_ready_passes_for_ready_manual_review_export(tmp_path, capsys) -> None:
    path = tmp_path / "ready.jsonl"
    rows = []
    for i in range(50):
        theorem_id = f"theorem-{i % 5}"
        rows.append(
            {
                "theorem_id": theorem_id,
                "uid": i % 10,
                "proof_script": f"theorem t_{i} : True := by trivial\n",
                "rubric": {"composite": 0.6 + i * 0.001},
                "proof_metrics": {
                    "proof_declaration_bytes": 500 + i,
                    "proof_declaration_lines": 20,
                    "proof_declaration_delimiters": 16,
                    "proof_declaration_max_depth": 4,
                    "probe_exit_code": 0,
                },
            },
        )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert main([str(path), "--require-decision-ready"]) == 0
    rendered = capsys.readouterr().out
    assert "decision_data_blockers=none" in rendered
    assert "comparison_theorems=5" in rendered
    assert "within_theorem_comparisons=theorems=5 rows=50" in rendered
    assert "corr_within_theorem(metric_bytes, judge_composite)=1.0000" in rendered
    assert "decision_ready=yes" in rendered
    assert "gate_verdict=manual_review_required" in rendered


def test_render_report_includes_within_theorem_centered_correlations(tmp_path, capsys) -> None:
    path = tmp_path / "within.jsonl"
    rows = []
    for theorem_idx in range(3):
        theorem_id = f"theorem-{theorem_idx}"
        rows.extend(
            [
                {
                    "theorem_id": theorem_id,
                    "uid": theorem_idx * 2,
                    "proof_script": f"theorem low_{theorem_idx} : True := by trivial\n",
                    "rubric": {"composite": 0.2},
                    "proof_metrics": {
                        "proof_declaration_bytes": 100,
                        "proof_declaration_lines": 10,
                        "proof_declaration_delimiters": 8,
                        "proof_declaration_max_depth": 3,
                        "probe_exit_code": 0,
                    },
                },
                {
                    "theorem_id": theorem_id,
                    "uid": theorem_idx * 2 + 1,
                    "proof_script": (
                        f"theorem high_{theorem_idx} : True := by\n"
                        "  have h : True := by trivial\n"
                        "  exact h\n"
                    ),
                    "rubric": {"composite": 0.8},
                    "proof_metrics": {
                        "proof_declaration_bytes": 200,
                        "proof_declaration_lines": 20,
                        "proof_declaration_delimiters": 16,
                        "proof_declaration_max_depth": 4,
                        "probe_exit_code": 0,
                    },
                },
            ],
        )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert main([str(path)]) == 0
    rendered = capsys.readouterr().out
    assert "comparison_theorems=3" in rendered
    assert "within_theorem_comparisons=theorems=3 rows=6" in rendered
    assert "corr_within_theorem(metric_bytes, judge_composite)=1.0000" in rendered
    assert "corr_within_theorem(metric_delimiters, judge_composite)=1.0000" in rendered


def test_render_report_flags_same_theorem_metric_judge_disagreements(tmp_path, capsys) -> None:
    path = tmp_path / "disagreement.jsonl"
    rows = [
        {
            "theorem_id": "same-theorem",
            "uid": 1,
            "proof_script": "theorem low_metric : True := by trivial\n",
            "rubric": {"composite": 0.8},
            "proof_metrics": {
                "proof_declaration_bytes": 100,
                "proof_declaration_lines": 10,
                "proof_declaration_delimiters": 8,
                "proof_declaration_max_depth": 3,
                "probe_exit_code": 0,
            },
        },
        {
            "theorem_id": "same-theorem",
            "uid": 2,
            "proof_script": "theorem high_metric : True := by\n  have h : True := by trivial\n  exact h\n",
            "rubric": {"composite": 0.7},
            "proof_metrics": {
                "proof_declaration_bytes": 300,
                "proof_declaration_lines": 20,
                "proof_declaration_delimiters": 18,
                "proof_declaration_max_depth": 4,
                "probe_exit_code": 0,
            },
        },
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert main([str(path)]) == 0
    rendered = capsys.readouterr().out
    assert "gate_verdict=research_only" in rendered
    assert "same_theorem_metric_judge_disagreements" in rendered
    assert "same_theorem_metric_judge_disagreements(metric_bytes):" in rendered
    assert "theorem=same-theorem high_line=2 high_uid=2 high_metric=300 high_judge=0.7000" in rendered
    assert "low_line=1 low_uid=1 low_metric=100 low_judge=0.8000" in rendered
    assert "metric_delta=200.0000 judge_delta=-0.1000" in rendered
    assert "same_theorem_metric_judge_disagreements(metric_delimiters):" in rendered
    assert "same_theorem_metric_judge_disagreements(proof_intrinsic):" in rendered


def test_require_decision_ready_requires_same_theorem_comparisons(tmp_path, capsys) -> None:
    path = tmp_path / "wide-only.jsonl"
    rows = []
    for i in range(50):
        rows.append(
            {
                "theorem_id": f"theorem-{i}",
                "uid": i % 10,
                "proof_script": f"theorem t_{i} : True := by trivial\n",
                "rubric": {"composite": 0.9},
                "proof_metrics": {
                    "proof_declaration_bytes": 500 + i,
                    "proof_declaration_lines": 20,
                    "proof_declaration_delimiters": 16,
                    "proof_declaration_max_depth": 4,
                    "probe_exit_code": 0,
                },
            },
        )
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

    assert main([str(path), "--require-decision-ready"]) == 2
    rendered = capsys.readouterr().out
    assert "comparison_theorems=0" in rendered
    assert "fewer_than_3_judged_theorems_with_2_rows_and_2_uids" in rendered
    assert "decision_ready=no" in rendered
