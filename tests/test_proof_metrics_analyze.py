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
    assert report.total_rows == 4
    assert report.invalid_json_lines == 1
    assert len(report.metric_rows) == 2

    outliers = padding_outliers(report.metric_rows, limit=1)
    assert outliers[0].theorem_id == "padded"

    rendered = render_report(report)
    assert "rows_with_proof_metrics=2" in rendered
    assert "corr(metric_bytes, proof_len_chars)=" in rendered
    assert "padding_outliers_by_proof_len_minus_metric_bytes:" in rendered


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
