from __future__ import annotations

import hashlib
import json
from pathlib import Path

from click.testing import CliRunner
from lemma.cli.main import main
from lemma.common.config import LemmaSettings
from lemma.dashboard import build_miner_dashboard, publish_public_dashboards, write_miner_dashboard
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


def _entry(target_id: str, *uids: int, include_proofs: bool = False) -> SolvedLedgerEntry:
    return SolvedLedgerEntry(
        target_id=target_id,
        solvers=tuple(
            LedgerSolver(
                uid=uid,
                hotkey=f"hotkey-{uid}",
                coldkey=f"coldkey-{uid}",
                proof_sha256=(
                    hashlib.sha256(_proof_script(uid).encode("utf-8")).hexdigest()
                    if include_proofs
                    else str(uid) * 64
                ),
                verify_reason="ok",
                build_seconds=float(uid),
                proof_script=_proof_script(uid) if include_proofs else None,
                proof_nonce=("n" * 64 if include_proofs else None),
                commitment_hash=("c" * 64 if include_proofs else None),
                commitment_block=(90 if include_proofs else None),
                commit_cutoff_block=(99 if include_proofs else None),
            )
            for uid in uids
        ),
        accepted_block=100,
        accepted_unix=200,
        validator_hotkey="validator-hotkey",
        lemma_version="0.1.0",
        theorem_statement_sha256=_target_hash(target_id),
    )


def _proof_script(uid: int) -> str:
    return (
        "import Mathlib\n\nnamespace Submission\n\n"
        "theorem target_1 : True := by\n"
        f"  trivial\n-- uid {uid}\n\nend Submission\n"
    )


def _target_hash(target_id: str) -> str:
    n = int(target_id.rsplit("_", 1)[1])
    return hashlib.sha256(f"import Mathlib\n\ntheorem target_{n} : True := by\n  sorry\n".encode()).hexdigest()


def _write_ledger(path: Path, *entries: SolvedLedgerEntry) -> Path:
    path.write_text("".join(entry.to_json_line() for entry in entries), encoding="utf-8")
    return path


def _campaign_registry(path: Path, *, status: str = "accepted") -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "lemma_formal_conjectures_campaigns_v1",
                "campaigns": [
                    {
                        "id": "fc.example",
                        "title": "Example bounty",
                        "status": status,
                        "source_url": "https://google-deepmind.github.io/formal-conjectures/",
                        "upstream_repo": "google-deepmind/formal-conjectures",
                        "upstream_commit": "abc123",
                        "lean_file": "FormalConjectures/Example.lean",
                        "declaration": "Example.theorem_one",
                        "statement_sha256": "a" * 64,
                        "reward_label": "1k SN467 alpha",
                        "type_expr": "True",
                        "challenge_full": "import Mathlib\n\ntheorem theorem_one : True := by\n  sorry\n",
                        "submission_stub": "import Mathlib\n\ntheorem theorem_one : True := by\n  sorry\n",
                        "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
                        "mathlib_rev": "5450b53e5ddc",
                    },
                ],
            },
        ),
        encoding="utf-8",
    )
    return path


def _acceptance_ledger(path: Path) -> Path:
    path.write_text(
        json.dumps(
            {
                "campaign_id": "fc.example",
                "solver_hotkey": "hotkey-full",
                "solver_uid": None,
                "proof_sha256": "b" * 64,
                "accepted_unix": 456,
                "reward_mode": "manual_winner_take_all_owner_emission",
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _settings(tmp_path: Path) -> LemmaSettings:
    return LemmaSettings(
        _env_file=None,
        problem_source="known_theorems",
        known_theorems_manifest_path=_manifest(tmp_path / "manifest.json"),
        solved_ledger_path=tmp_path / "ledger.jsonl",
    )


def test_miner_dashboard_empty_ledger_marks_first_target_active(tmp_path: Path) -> None:
    payload = build_miner_dashboard(_settings(tmp_path), generated_unix=1)

    assert payload["schema_version"] == 5
    assert payload["generated_unix"] == 1
    assert payload["problem_source"] == "known_theorems"
    assert payload["seed"] == 0
    assert payload["cadence"]["window_blocks"] == 100
    assert payload["cadence"]["variants_enabled"] is True
    assert payload["counts"]["total_targets"] == 2
    assert payload["active_target"]["id"] == "known/test/target_1"
    assert payload["target_window"]["previous"]["id"] == "known/test/target_1"
    assert payload["target_window"]["current"]["id"] == "known/test/target_1"
    assert payload["target_window"]["next"]["id"] == "known/test/target_2"
    assert [target["status"] for target in payload["targets"]] == ["previous", "current", "next"]


def test_miner_dashboard_solved_ledger_does_not_advance_cadence_target(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 7))

    payload = build_miner_dashboard(settings, generated_unix=1, current_block=100)

    assert payload["active_target"]["id"] == "known/test/target_2"
    assert payload["target_window"]["previous"]["id"] == "known/test/target_1"
    assert payload["target_window"]["current"]["id"] == "known/test/target_2"
    assert payload["target_window"]["next"]["id"] == "known/test/target_1"
    assert payload["targets"][0]["solved"]["solver_uids"] == [7]
    assert payload["targets"][0]["solved"]["solver_hotkeys"] == ["hotkey-7"]
    assert payload["current_solver_set"]["solvers"][0]["uid"] == 7
    assert payload["current_solver_set"]["solvers"][0]["hotkey"] == "hotkey-7"


def test_miner_dashboard_ignores_stale_ledger_hash(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    stale = _entry("known/test/target_1", 7)
    stale = SolvedLedgerEntry(
        target_id=stale.target_id,
        solvers=stale.solvers,
        accepted_block=stale.accepted_block,
        accepted_unix=stale.accepted_unix,
        validator_hotkey=stale.validator_hotkey,
        lemma_version=stale.lemma_version,
        theorem_statement_sha256="bad",
    )
    _write_ledger(settings.solved_ledger_path, stale)

    payload = build_miner_dashboard(settings, generated_unix=1)

    assert payload["counts"]["accepted_targets"] == 0
    assert payload["active_target"]["id"] == "known/test/target_1"
    assert payload["solved_ledger"] == []
    assert payload["accepted_solver_receipts"] == []


def test_miner_dashboard_exports_public_accepted_solver_receipts(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 7, include_proofs=True))

    payload = build_miner_dashboard(settings, generated_unix=1)
    receipts = payload["accepted_solver_receipts"]

    assert payload["counts"]["accepted_solver_receipts"] == 1
    assert receipts[0]["target_id"] == "known/test/target_1"
    assert receipts[0]["solver_uid"] == 7
    assert receipts[0]["solver_hotkey"] == "hotkey-7"
    assert receipts[0]["validator_hotkey"] == "validator-hotkey"
    assert "proof_sha256" not in receipts[0]
    assert "proof_nonce" not in receipts[0]
    assert "commitment_hash" not in receipts[0]


def test_miner_dashboard_tied_solvers_split_current_weight(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 2, 3))

    payload = build_miner_dashboard(settings, generated_unix=1, current_block=100)

    solvers = payload["current_solver_set"]["solvers"]
    assert [solver["uid"] for solver in solvers] == [2, 3]
    assert [solver["weight_share"] for solver in solvers] == [0.5, 0.5]


def test_miner_dashboard_keeps_cadence_target_even_if_all_known_targets_have_receipts(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(
        settings.solved_ledger_path,
        _entry("known/test/target_1", 2),
        _entry("known/test/target_2", 3),
    )

    payload = build_miner_dashboard(settings, generated_unix=1)

    assert payload["active_target"]["id"] == "known/test/target_1"
    assert payload["target_window"]["current"]["id"] == "known/test/target_1"
    assert payload["counts"]["accepted_targets"] == 2


def test_miner_dashboard_omits_private_or_local_fields(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 2, include_proofs=True))

    text = json.dumps(build_miner_dashboard(settings, generated_unix=1), sort_keys=True)

    assert "proof_script" not in text
    assert "proof_sha256" not in text
    assert "commitment_hash" not in text
    assert "validator-hotkey" in text
    assert str(tmp_path) not in text


def test_miner_dashboard_hybrid_source_includes_generated_cadence(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(update={"problem_source": "hybrid"})

    payload = build_miner_dashboard(settings, generated_unix=1)

    assert payload["problem_source"] == "hybrid"
    assert payload["counts"]["total_targets"] > 2
    assert any(target["id"].startswith("gen/") for target in payload["targets"])


def test_dashboard_export_cli_writes_json(monkeypatch, tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "manifest.json")
    output = tmp_path / "cadence.json"
    monkeypatch.setattr("lemma.dashboard.time.time", lambda: 123.0)

    result = CliRunner().invoke(
        main,
        ["dashboard", "export", "--output", str(output)],
        env={
            "LEMMA_PROBLEM_SOURCE": "known_theorems",
            "LEMMA_KNOWN_THEOREMS_MANIFEST_PATH": str(manifest),
            "LEMMA_LEDGER_PATH": str(tmp_path / "ledger.jsonl"),
        },
    )

    assert result.exit_code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 5
    assert payload["generated_unix"] == 123
    assert payload["active_target"]["id"] == "known/test/target_1"
    assert payload["target_window"]["current"]["id"] == "known/test/target_1"
    assert "wrote=" in result.output


def test_write_miner_dashboard_creates_parent_directory(tmp_path: Path) -> None:
    output = tmp_path / "data" / "cadence.json"

    write_miner_dashboard(output, {"schema_version": 1})

    assert json.loads(output.read_text(encoding="utf-8")) == {"schema_version": 1}


def test_publish_public_dashboards_writes_safe_atomic_feeds(tmp_path: Path) -> None:
    settings = _settings(tmp_path).model_copy(
        update={
            "formal_campaign_registry_path": _campaign_registry(tmp_path / "campaigns.json"),
            "campaign_acceptance_ledger_path": _acceptance_ledger(tmp_path / "campaign-ledger.jsonl"),
        },
    )
    _write_ledger(settings.solved_ledger_path, _entry("known/test/target_1", 7, include_proofs=True))

    cadence_path, bounties_path = publish_public_dashboards(tmp_path / "live", settings)

    cadence = json.loads(cadence_path.read_text(encoding="utf-8"))
    bounties = json.loads(bounties_path.read_text(encoding="utf-8"))
    combined = json.dumps({"cadence": cadence, "bounties": bounties}, sort_keys=True)
    assert cadence["schema_version"] == 5
    assert bounties["campaigns"][0]["accepted"]["solver_hotkey"] == "hotkey-full"
    assert "solver_uid" not in bounties["campaigns"][0]["accepted"]
    assert "proof_script" not in combined
    assert "proof_sha256" not in combined
    assert "commitment_hash" not in combined
    assert not list((tmp_path / "live").glob(".*.tmp"))


def test_dashboard_publish_cli_writes_both_json_files(monkeypatch, tmp_path: Path) -> None:
    manifest = _manifest(tmp_path / "manifest.json")
    registry = _campaign_registry(tmp_path / "campaigns.json", status="open")
    output_dir = tmp_path / "live"
    monkeypatch.setattr("lemma.dashboard.time.time", lambda: 123.0)

    result = CliRunner().invoke(
        main,
        ["dashboard", "publish", "--output-dir", str(output_dir)],
        env={
            "LEMMA_KNOWN_THEOREMS_MANIFEST_PATH": str(manifest),
            "LEMMA_LEDGER_PATH": str(tmp_path / "ledger.jsonl"),
            "LEMMA_FORMAL_CAMPAIGNS_PATH": str(registry),
            "LEMMA_CAMPAIGN_ACCEPTANCE_LEDGER_PATH": str(tmp_path / "campaign-ledger.jsonl"),
        },
    )

    assert result.exit_code == 0
    assert json.loads((output_dir / "cadence.json").read_text(encoding="utf-8"))["generated_unix"] == 123
    assert json.loads((output_dir / "bounties.json").read_text(encoding="utf-8"))["generated_unix"] == 123
    assert "wrote=" in result.output
