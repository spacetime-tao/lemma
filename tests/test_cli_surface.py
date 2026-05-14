"""Public Lemma CLI surface."""

import tomllib
from pathlib import Path

from click.testing import CliRunner
from lemma.cli.main import main
from lemma.lean.sandbox import VerifyResult


def test_public_script_is_lemma_only() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]

    assert main.name == "lemma"
    assert scripts == {"lemma": "lemma.cli.main:main"}


def test_home_screen_lists_wta_commands() -> None:
    result = CliRunner().invoke(main)

    assert result.exit_code == 0
    assert "target" in result.output
    assert "submit" in result.output
    assert "verify" in result.output
    assert "miner" in result.output
    assert "validator" in result.output
    assert "preview" not in result.output
    assert "prover" not in result.output


def test_removed_public_commands_fail() -> None:
    for command in [
        ("preview",),
        ("problems",),
        ("status",),
        ("doctor",),
        ("setup",),
        ("configure",),
        ("configure", "prover"),
        ("configure", "prover-model"),
        ("configure", "prover-retries"),
        ("target", "review"),
        ("miner", "dry-run"),
    ]:
        result = CliRunner().invoke(main, [*command, "--help"])
        assert result.exit_code != 0
        assert "No such command" in result.output


def test_submit_command_accepts_problem_and_submission_options() -> None:
    result = CliRunner().invoke(main, ["submit", "--help"])

    assert result.exit_code == 0
    assert "--problem" in result.output
    assert "--submission" in result.output
    assert "--verify" in result.output
    assert "--no-verify" in result.output


def test_submit_rejects_unknown_target_id(tmp_path: Path) -> None:
    submission = tmp_path / "Submission.lean"
    submission.write_text("import Mathlib\n", encoding="utf-8")

    result = CliRunner().invoke(
        main,
        ["submit", "--problem", "unknown/target", "--submission", str(submission)],
    )

    assert result.exit_code != 0
    assert "unknown target id: unknown/target" in result.output


def test_submit_verifies_by_default(monkeypatch, tmp_path: Path) -> None:
    submission = tmp_path / "Submission.lean"
    submission.write_text("import Mathlib\n", encoding="utf-8")
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=True, reason="ok", build_seconds=1.25)

    monkeypatch.setattr("lemma.lean.verify_runner.run_lean_verify", fake_run_lean_verify)

    result = CliRunner().invoke(
        main,
        [
            "submit",
            "--problem",
            "known/smoke/nat_two_plus_two_eq_four",
            "--submission",
            str(submission),
        ],
    )

    assert result.exit_code == 0
    assert "Valid proof stored" in result.output
    assert "target_id=known/smoke/nat_two_plus_two_eq_four" in result.output
    assert "verified=true" in result.output
    assert "verify_reason=ok" in result.output
    assert "build_seconds=1.25" in result.output
    assert "ready_to_serve=true" in result.output
    assert store.exists()


def test_submit_no_verify_labels_unconfirmed(monkeypatch, tmp_path: Path) -> None:
    submission = tmp_path / "Submission.lean"
    submission.write_text("import Mathlib\n", encoding="utf-8")
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(tmp_path / "submissions.json"))

    result = CliRunner().invoke(
        main,
        [
            "submit",
            "--problem",
            "known/smoke/nat_two_plus_two_eq_four",
            "--submission",
            str(submission),
            "--no-verify",
        ],
    )

    assert result.exit_code == 0
    assert "Proof stored without validity confirmation" in result.output
    assert "verified=false" in result.output
    assert "verify_reason=not_run" in result.output
    assert "ready_to_serve=false" in result.output


def test_verify_command_accepts_problem_and_submission_options() -> None:
    result = CliRunner().invoke(main, ["verify", "--help"])

    assert result.exit_code == 0
    assert "--problem" in result.output
    assert "--submission" in result.output


def test_miner_help_lists_manual_subcommands() -> None:
    result = CliRunner().invoke(main, ["miner", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output
    assert "observability" not in result.output


def test_validator_help_lists_wta_subcommands() -> None:
    result = CliRunner().invoke(main, ["validator", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output
    assert "dry-run" in result.output
    assert "check" in result.output
    assert "config" not in result.output


def test_target_command_shows_active_known_theorem(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "wta-ledger.jsonl"))

    result = CliRunner().invoke(main, ["target", "show"])

    assert result.exit_code == 0
    assert "Lemma target" in result.output
    assert "known/smoke/nat_two_plus_two_eq_four" in result.output
    assert "proof_reference=" in result.output


def test_target_ledger_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "wta-ledger.jsonl"))

    result = CliRunner().invoke(main, ["target", "ledger"])

    assert result.exit_code == 0
    assert "No solved targets yet." in result.output
