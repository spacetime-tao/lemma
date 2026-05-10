"""Offline sybil/Pareto replay analyzer."""

import json
from pathlib import Path

import pytest
from tools.sybil_replay_analyze import clone_pressure, decision_ready, load_report, main, render_report, replay_epoch


def _row(
    *,
    block: int = 100,
    theorem_id: str = "t",
    theorem_statement: str | None = None,
    uid: int,
    composite: float,
    proof: str = "theorem t : True := by trivial\n",
    trace: str = "clear proof",
    coldkey: str | None = None,
) -> dict:
    row = {
        "schema_version": 1,
        "block": block,
        "theorem_id": theorem_id,
        "uid": uid,
        "reasoning_text": trace,
        "proof_script": proof,
        "rubric": {
            "coherence": composite,
            "exploration": composite,
            "clarity": composite,
            "composite": composite,
        },
    }
    if theorem_statement is not None:
        row["theorem_statement"] = theorem_statement
    if coldkey is not None:
        row["coldkey"] = coldkey
    return row


def _write_jsonl(path: Path, rows: list[dict], *, bad_json: bool = False) -> None:
    text = "\n".join(json.dumps(row) for row in rows)
    if bad_json:
        text += "\n{bad json"
    path.write_text(text + "\n", encoding="utf-8")


def test_replay_compares_dedup_modes_and_clone_pressure(tmp_path) -> None:
    path = tmp_path / "train.jsonl"
    _write_jsonl(
        path,
        [
            _row(uid=1, composite=1.0),
            _row(uid=2, composite=0.8, proof="theorem u : True := by trivial\n", trace="short"),
            _row(uid=3, composite=1.0),  # exact duplicate of uid 1
            {"schema_version": 2, "uid": 4},
        ],
        bad_json=True,
    )

    report = load_report(path, proof_weight=0.0)
    assert report.total_rows == 5
    assert report.invalid_json_lines == 1
    assert len(report.replay_rows) == 3
    assert decision_ready(report) is False

    base = replay_epoch(report.replay_rows, name="base", identical_dedup=True, coldkey_dedup=True)
    assert base.identical_dropped == 1
    assert 3 not in base.weights

    no_identical = replay_epoch(
        report.replay_rows,
        name="no_identical",
        identical_dedup=False,
        coldkey_dedup=True,
    )
    assert no_identical.identical_dropped == 0
    assert 3 in no_identical.weights

    exact = clone_pressure(report.replay_rows, clone_k=2, rewrite=False)
    rewritten = clone_pressure(report.replay_rows, clone_k=2, rewrite=True)
    assert exact is not None
    assert rewritten is not None
    assert exact.extra_share == pytest.approx(0.0)
    assert rewritten.extra_share > exact.extra_share

    rendered = render_report(report, clone_k=2)
    assert "Sybil/Pareto replay analysis" in rendered
    assert "rows_replayable=3" in rendered
    assert "coldkey_note=no coldkeys in export" in rendered
    assert "decision_ready=no" in rendered
    assert "clone_k=2" in rendered
    assert "summary_exact_clone_extra_share: n=1 max=0.0000 mean=0.0000" in rendered
    assert "summary_rewritten_clone_extra_share: n=1" in rendered
    assert "summary_rewritten_clone_group_share: n=1" in rendered
    assert "base: weighted_uids=2" in rendered
    assert "no_identical_dedup: weighted_uids=3" in rendered
    assert "exact_clone_k=2:" in rendered
    assert "rewritten_clone_k=2:" in rendered


def test_replay_uses_coldkey_rows_when_present(tmp_path) -> None:
    path = tmp_path / "train.jsonl"
    _write_jsonl(
        path,
        [
            _row(uid=1, composite=0.9, coldkey="same"),
            _row(uid=2, composite=0.8, proof="theorem u : True := by trivial\n", trace="other", coldkey="same"),
        ],
    )
    rows = load_report(path, proof_weight=0.0).replay_rows

    base = replay_epoch(rows, name="base", identical_dedup=True, coldkey_dedup=True)
    no_coldkey = replay_epoch(rows, name="no_coldkey", identical_dedup=True, coldkey_dedup=False)

    assert base.coldkey_dropped == 1
    assert set(base.weights) == {1}
    assert no_coldkey.coldkey_dropped == 0
    assert set(no_coldkey.weights) == {1, 2}


def test_replay_fingerprint_uses_theorem_statement_when_present(tmp_path) -> None:
    path = tmp_path / "train.jsonl"
    _write_jsonl(
        path,
        [
            _row(uid=1, composite=0.9, theorem_id="same-id", theorem_statement="theorem a : True := by sorry"),
            _row(uid=2, composite=0.9, theorem_id="same-id", theorem_statement="theorem b : True := by sorry"),
        ],
    )
    rows = load_report(path, proof_weight=0.0).replay_rows

    base = replay_epoch(rows, name="base", identical_dedup=True, coldkey_dedup=True)

    assert base.identical_dropped == 0
    assert set(base.weights) == {1, 2}


def test_main_uses_env_path(tmp_path, monkeypatch, capsys) -> None:
    path = tmp_path / "train.jsonl"
    _write_jsonl(path, [_row(uid=1, composite=0.9)])
    monkeypatch.setenv("LEMMA_TRAINING_EXPORT_JSONL", str(path))

    assert main(["--clone-k", "1", "--epochs", "1", "--proof-weight", "0"]) == 0
    rendered = capsys.readouterr().out
    assert "rows_replayable=1" in rendered
    assert "exact_clone_k=1:" in rendered


def test_require_decision_ready_returns_nonzero_for_blocked_export(tmp_path, capsys) -> None:
    path = tmp_path / "train.jsonl"
    _write_jsonl(path, [_row(uid=1, composite=0.9)])

    assert main([str(path), "--require-decision-ready"]) == 2
    rendered = capsys.readouterr().out
    assert "decision_ready=no" in rendered
    assert "replayable_rows<50" in rendered


def test_require_decision_ready_passes_for_ready_export(tmp_path, capsys) -> None:
    path = tmp_path / "train.jsonl"
    rows = [
        _row(
            block=100 + i // 10,
            theorem_id=f"t{i % 5}",
            uid=(i % 5) + 1,
            composite=0.8 + (i % 5) / 100,
            proof=f"theorem t{i} : True := by trivial\n",
            trace=f"trace {i}",
            coldkey=f"cold-{(i % 5) + 1}",
        )
        for i in range(50)
    ]
    _write_jsonl(path, rows)

    report = load_report(path, proof_weight=0.0)
    assert decision_ready(report) is True
    assert main([str(path), "--require-decision-ready", "--proof-weight", "0"]) == 0
    rendered = capsys.readouterr().out
    assert "decision_data_blockers=none" in rendered
    assert "decision_ready=yes" in rendered
