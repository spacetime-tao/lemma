"""Offline proof-metrics export analyzer."""

import json

from tools.proof_metrics_analyze import load_report, main, padding_outliers, render_report


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
    assert "corr(metric_bytes, proof_len_chars)=" in rendered
    assert "padding_outliers_by_proof_len_minus_metric_bytes:" in rendered
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
    assert "rows_with_proof_metrics=1" in capsys.readouterr().out
