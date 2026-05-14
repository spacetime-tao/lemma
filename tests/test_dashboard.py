from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner
from lemma.cli.main import main
from lemma.common.config import LemmaSettings
from lemma.dashboard import build_miner_dashboard, write_miner_dashboard
from lemma.ledger import LedgerSolver, SolvedLedgerEntry


def _manifest(path: Path, count: int = 2) -> Path:
    targets = []
    for idx in range(count):
        n = idx + 1
        targets.append(
            {
                "id": f"known/test/target_{n}",
                "order": n,
                "title": f"Target {n}",
                "difficulty": "smoke",
                "imports": ["Mathlib"],
                "theorem_name": f"target_{n}",
                "type_expr": "True",
                "challenge_full": f"import Mathlib\n\ntheorem target_{n} : True := by\n  sorry\n",
                "submission_stub": (
                    f"import Mathlib\n\nnamespace Submission\n\ntheorem target_{n} : True := by\n"
                    "  sorry\n\nend Submission\n"
                ),
                "human_proof_reference": {"citation": "test citation"},
                "attribution": {"source": "test"},
                "review": {
                    "known_math": True,
                    "already_formalized_in_lean": False,
                    "accepted_lean_proof_known": False,
                    "reviewer": "test",
                    "reviewed_at": "2026-05-14",
                    "duplicate_check": "none",
                    "statement_faithfulness": "ok",
                },
            },
        )
    data = {
        "schema_version": 1,
        "source": {
            "repo": "test",
            "commit": "abc123",
            "lean_toolchain": "lean",
            "mathlib_rev": "mathlib",
            "license_note": "test",
        },
        "targets": targets,
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _entry(target_id: str, *uids: int) -> SolvedLedgerEntry:
    return SolvedLedgerEntry(
        target_id=target_id,
        solvers=tuple(
            LedgerSolver(
                uid=uid,
                hotkey=f"hotkey-{uid}",
                coldkey=f"coldkey-{uid}",
                proof_sha256=str(uid) * 64,
                verify_reason="ok",
                build_seconds=float(uid),
            )
            for uid in uids
        ),
        accepted_block=100,
        accepted_unix=200,
        validator_hotkey="validator-hotkey",
        lemma_version="0.1.0",
        theorem_statement_sha256="a" * 64,
    )


def _write_ledger(path: Path, *entries: SolvedLedgerEntry) -> Path:
    path.write_text("".join(entry.to_json_line() for entry in entries), encoding="utf-8")
    return path


def _settings(tmp_path: Path) -> LemmaSettings:
    return LemmaSettings(
        _env_file=None,
        known_theorems_manifest_path=_manifest(tmp_path / "manifest.json"),
        solved_ledger_path=tmp_path / "ledger.jsonl",
    )


def test_miner_dashboard_empty_ledger_marks_first_target_active(tmp_path: Path) -> None:
    payload = build_miner_dashboard(_settings(tmp_path), generated_unix=1)

    assert payload["schema_version"] == 1
    assert payload["generated_unix"] == 1
    assert payload["counts"]["total_targets"] == 2
    assert payload["counts"]["solved_targets"] == 0
    assert payload["active_target"]["id"] == "known/test/target_1"
    assert payload["targets"][0]["status"] == "active"
    assert payload["targets"][1]["status"] == "queued"


def test_miner_dashboard_one_solve_advances_active_target(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 7))

    payload = build_miner_dashboard(settings, generated_unix=1)

    assert payload["counts"]["solved_targets"] == 1
    assert payload["counts"]["remaining_targets"] == 1
    assert payload["active_target"]["id"] == "known/test/target_2"
    assert payload["targets"][0]["status"] == "solved"
    assert payload["targets"][0]["solved"]["solver_uids"] == [7]
    assert payload["current_solver_set"]["solvers"][0]["uid"] == 7
    assert payload["current_solver_set"]["solvers"][0]["hotkey"] == "hotkey-7"
    assert payload["current_solver_set"]["solvers"][0]["proof_sha256"] == "7" * 64


def test_miner_dashboard_tied_solvers_split_current_weight(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 2, 3))

    payload = build_miner_dashboard(settings, generated_unix=1)

    solvers = payload["current_solver_set"]["solvers"]
    assert [solver["uid"] for solver in solvers] == [2, 3]
    assert [solver["weight_share"] for solver in solvers] == [0.5, 0.5]


def test_miner_dashboard_all_solved_has_no_active_target(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(
        settings.solved_ledger_path,
        _entry("known/test/target_1", 2),
        _entry("known/test/target_2", 3),
    )

    payload = build_miner_dashboard(settings, generated_unix=1)

    assert payload["active_target"] is None
    assert payload["counts"]["remaining_targets"] == 0
    assert [target["status"] for target in payload["targets"]] == ["solved", "solved"]


def test_miner_dashboard_omits_private_or_local_fields(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 2))

    text = json.dumps(build_miner_dashboard(settings, generated_unix=1), sort_keys=True)

    assert "proof_script" not in text
    assert "coldkey" not in text
    assert "validator-hotkey" not in text
    assert str(tmp_path) not in text


def test_dashboard_export_cli_writes_json(monkeypatch, tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "manifest.json")
    output = tmp_path / "miner-dashboard.json"
    monkeypatch.setattr("lemma.dashboard.time.time", lambda: 123.0)

    result = CliRunner().invoke(
        main,
        ["dashboard", "export", "--output", str(output)],
        env={
            "LEMMA_KNOWN_THEOREMS_MANIFEST_PATH": str(manifest),
            "LEMMA_LEDGER_PATH": str(tmp_path / "ledger.jsonl"),
        },
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    assert payload["generated_unix"] == 123
    assert payload["active_target"]["id"] == "known/test/target_1"
    assert "wrote=" in result.output


def test_write_miner_dashboard_creates_parent_directory(tmp_path: Path) -> None:
    output = tmp_path / "data" / "miner-dashboard.json"

    write_miner_dashboard(output, {"schema_version": 1})

    assert json.loads(output.read_text(encoding="utf-8")) == {"schema_version": 1}
