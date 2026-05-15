"""Public Lemma CLI surface."""

import tomllib
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import click
from click.testing import CliRunner
from lemma.cli.main import main
from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import VerifyResult


def test_public_script_is_lemma_only() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]

    assert main.name == "lemma"
    assert scripts == {"lemma": "lemma.cli.main:main"}


def test_home_screen_lists_proof_commands() -> None:
    result = CliRunner().invoke(main)

    assert result.exit_code == 0
    assert "setup" in result.output
    assert "mine" in result.output
    assert "status" in result.output
    assert "validate" in result.output
    assert "\n  target" not in result.output
    assert "\n  submit" not in result.output
    assert "\n  verify" not in result.output
    assert "\n  miner" not in result.output
    assert "\n  dashboard" not in result.output
    assert "\n  portal" not in result.output
    assert "\n  validator" not in result.output
    assert "preview" not in result.output
    assert "prover" not in result.output


def test_removed_commands_fail() -> None:
    for command in [
        ("preview",),
        ("problems",),
        ("doctor",),
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


def test_advanced_commands_are_hidden_but_callable() -> None:
    for command in [
        ("target",),
        ("submit",),
        ("commit",),
        ("miner",),
        ("validator",),
        ("verify",),
        ("dashboard",),
        ("portal",),
        ("meta",),
    ]:
        result = CliRunner().invoke(main, [*command, "--help"])
        assert result.exit_code == 0


def test_submit_command_accepts_problem_and_submission_options() -> None:
    result = CliRunner().invoke(main, ["submit", "--help"])

    assert result.exit_code == 0
    assert "--problem" in result.output
    assert "--submission" in result.output
    assert "--paste" in result.output
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
    assert "Lean accepted this proof" in result.output
    assert "Checking proof with Lean" in result.output
    assert "target_id=known/smoke/nat_two_plus_two_eq_four" in result.output
    assert "verified=true" in result.output
    assert "verify_reason=ok" in result.output
    assert "build_seconds=1.25" in result.output
    assert "commit_status=uncommitted" in result.output
    assert "ready_to_reveal=false" in result.output
    assert "lemma commit --problem known/smoke/nat_two_plus_two_eq_four" in result.output
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
    assert "Proof stored without local Lean check" in result.output
    assert "verified=false" in result.output
    assert "verify_reason=not_run" in result.output
    assert "commit_status=uncommitted" in result.output
    assert "ready_to_reveal=false" in result.output


def test_submit_interactive_decline_shows_active_target(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "solved-ledger.jsonl"))
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(tmp_path / "submissions.json"))

    result = CliRunner().invoke(main, ["submit"], input="n\n")

    assert result.exit_code == 0
    assert "Lemma submit" in result.output
    assert "Current theorem" in result.output
    assert "known/smoke/nat_two_plus_two_eq_four" in result.output
    assert "Ready to enter a proof" in result.output
    assert "No proof stored" in result.output
    assert not (tmp_path / "submissions.json").exists()


def test_submit_interactive_editor_stores_verified_proof(monkeypatch, tmp_path: Path) -> None:
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "solved-ledger.jsonl"))
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))

    proof = """import Mathlib

namespace Submission

theorem nat_two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by
  rfl

end Submission
"""

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=True, reason="ok", build_seconds=0.5)

    monkeypatch.setattr("click.edit", lambda **kwargs: proof)
    monkeypatch.setattr("lemma.lean.verify_runner.run_lean_verify", fake_run_lean_verify)
    result = CliRunner().invoke(main, ["submit"], input="y\n")

    assert result.exit_code == 0
    assert "Opening Submission.lean in your editor" in result.output
    assert "Lean accepted this proof" in result.output
    assert store.exists()


def test_submit_interactive_paste_stores_verified_proof(monkeypatch, tmp_path: Path) -> None:
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "solved-ledger.jsonl"))
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    proof = (
        "import Mathlib\n\nnamespace Submission\n\n"
        "theorem nat_two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by\n"
        "  rfl\n\nend Submission\n"
    )

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=True, reason="ok", build_seconds=0.25)

    monkeypatch.setattr("lemma.lean.verify_runner.run_lean_verify", fake_run_lean_verify)
    result = CliRunner().invoke(main, ["submit", "--paste"], input="y\n" + proof)

    assert result.exit_code == 0
    assert "Paste your full Submission.lean file" in result.output
    assert "Lean accepted this proof" in result.output
    assert store.exists()


def test_submit_interactive_editor_unchanged_aborts(monkeypatch, tmp_path: Path) -> None:
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "solved-ledger.jsonl"))
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))

    def unchanged_edit(**kwargs):
        return str(kwargs["text"])

    monkeypatch.setattr("click.edit", unchanged_edit)

    result = CliRunner().invoke(main, ["submit"], input="y\n")

    assert result.exit_code == 0
    assert "empty or unchanged" in result.output
    assert not store.exists()


def test_submit_verify_failure_does_not_store(monkeypatch, tmp_path: Path) -> None:
    submission = tmp_path / "Submission.lean"
    submission.write_text("import Mathlib\n", encoding="utf-8")
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=False, reason="compile_error", stderr_tail="nope")

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

    assert result.exit_code != 0
    assert "Lean rejected this proof" in result.output
    assert "nope" in result.output
    assert not store.exists()


def test_submit_verify_infra_failure_does_not_traceback(monkeypatch, tmp_path: Path) -> None:
    submission = tmp_path / "Submission.lean"
    submission.write_text("import Mathlib\n", encoding="utf-8")
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))

    def fake_run_lean_verify(*args, **kwargs):
        raise RuntimeError("docker unavailable")

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

    assert result.exit_code != 0
    assert "Lean could not run local verification" in result.output
    assert "Traceback" not in result.output
    assert not store.exists()


def test_submit_rejects_paste_with_submission(tmp_path: Path) -> None:
    submission = tmp_path / "Submission.lean"
    submission.write_text("import Mathlib\n", encoding="utf-8")

    result = CliRunner().invoke(main, ["submit", "--paste", "--submission", str(submission)])

    assert result.exit_code != 0
    assert "Use either --paste or --submission" in result.output


def test_mine_accepts_pasted_proof_commits_and_starts(monkeypatch, tmp_path: Path) -> None:
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "solved-ledger.jsonl"))
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    proof = (
        "import Mathlib\n\nnamespace Submission\n\n"
        "theorem nat_two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by\n"
        "  rfl\n\nend Submission\n"
    )
    started: list[bool] = []

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=True, reason="ok", build_seconds=0.25)

    monkeypatch.setattr("lemma.lean.verify_runner.run_lean_verify", fake_run_lean_verify)
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", _committed_entry)
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(True))

    result = CliRunner().invoke(main, ["mine"], input="y\n" + proof)

    assert result.exit_code == 0
    assert "Active theorem" in result.output
    assert "Submit a proof now?" in result.output
    assert "Your private commitment is on-chain" in result.output
    assert "Starting miner now" in result.output
    assert started == [True]
    assert store.exists()


def test_mine_chain_commit_failure_keeps_retryable_store(monkeypatch, tmp_path: Path) -> None:
    submission = tmp_path / "Submission.lean"
    submission.write_text("import Mathlib\n", encoding="utf-8")
    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=True, reason="ok", build_seconds=0.0)

    def fail_commit(settings, problem, entry):
        raise click.ClickException(
            f"Proof stored, but chain commitment failed. Run `lemma commit --problem {problem.id}`.",
        )

    monkeypatch.setattr("lemma.lean.verify_runner.run_lean_verify", fake_run_lean_verify)
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", fail_commit)

    result = CliRunner().invoke(
        main,
        [
            "mine",
            "--submission",
            str(submission),
        ],
    )

    assert result.exit_code != 0
    assert "Lean accepted this proof" in result.output
    assert "lemma commit --problem known/smoke/nat_two_plus_two_eq_four" in result.output
    assert store.exists()


def test_commit_retries_stored_proof(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    problem = resolve_problem(
        LemmaSettings(_env_file=None, miner_submissions_path=store),
        "known/smoke/nat_two_plus_two_eq_four",
    )
    save_pending_submission(store, problem, "import Mathlib\n", proof_nonce="n" * 64)
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", _committed_entry)

    result = CliRunner().invoke(
        main,
        ["commit", "--problem", "known/smoke/nat_two_plus_two_eq_four"],
    )

    assert result.exit_code == 0
    assert "Proof commitment published" in result.output
    assert "commitment_hash=" + ("c" * 64) in result.output


def test_mine_retry_commit_starts_miner(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    started: list[bool] = []
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    settings = LemmaSettings(_env_file=None, miner_submissions_path=store)
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    save_pending_submission(store, problem, "import Mathlib\n", proof_nonce="n" * 64)
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", _committed_entry)
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(True))

    result = CliRunner().invoke(main, ["mine", "--retry-commit"])

    assert result.exit_code == 0
    assert "Commitment published" in result.output
    assert started == [True]


def test_mine_retry_commit_rejects_legacy_stored_proof(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    settings = LemmaSettings(_env_file=None, miner_submissions_path=store)
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    save_pending_submission(store, problem, "import Mathlib\n")

    result = CliRunner().invoke(main, ["mine", "--retry-commit"])

    assert result.exit_code != 0
    assert "older format" in result.output
    assert "lemma mine --replace" in result.output


def test_mine_replace_overwrites_stale_proof(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    started: list[bool] = []
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    settings = LemmaSettings(_env_file=None, miner_submissions_path=store)
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    save_pending_submission(store, problem, "import Mathlib\n")

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=True, reason="ok", build_seconds=0.0)

    monkeypatch.setattr("lemma.lean.verify_runner.run_lean_verify", fake_run_lean_verify)
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", _committed_entry)
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(True))

    result = CliRunner().invoke(main, ["mine", "--replace", "--submission", str(_proof_file(tmp_path))])

    assert result.exit_code == 0
    assert "Replacing the stored proof" in result.output
    assert "Your private commitment is on-chain" in result.output
    assert started == [True]


def test_mine_refreshes_genesis_and_retries_commit_when_window_closes(monkeypatch, tmp_path: Path) -> None:
    from lemma.cli.main import CommitWindowClosedError

    store = tmp_path / "submissions.json"
    ledger = tmp_path / "ledger.jsonl"
    calls: list[int | None] = []
    started: list[int | None] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(ledger))
    monkeypatch.setenv("LEMMA_TARGET_GENESIS_BLOCK", "100")

    def fake_run_lean_verify(*args, **kwargs):
        return VerifyResult(passed=True, reason="ok", build_seconds=84.53)

    def fake_publish(settings, problem, entry):
        calls.append(settings.target_genesis_block)
        if len(calls) == 1:
            raise CommitWindowClosedError("closed", current_block=130, entry=entry)
        return replace(entry, commitment_status="committed", committed_block=130, reveal_block=155)

    monkeypatch.setattr("lemma.lean.verify_runner.run_lean_verify", fake_run_lean_verify)
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", fake_publish)
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(settings.target_genesis_block))

    result = CliRunner().invoke(main, ["mine", "--submission", str(_proof_file(tmp_path))], input="y\n")

    assert result.exit_code == 0
    assert "Commit window closed while this proof was being prepared." in result.output
    assert "Refresh the first target window and retry the commitment now?" in result.output
    assert "Updated .env" in result.output
    assert "Your private commitment is on-chain" in result.output
    assert calls == [100, 130]
    assert started == [130]
    assert "LEMMA_TARGET_GENESIS_BLOCK=130" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_status_prefers_setup_when_genesis_missing(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.delenv("LEMMA_TARGET_GENESIS_BLOCK", raising=False)
    problem = resolve_problem(
        LemmaSettings(_env_file=None, miner_submissions_path=store),
        "known/smoke/nat_two_plus_two_eq_four",
    )
    save_pending_submission(store, problem, "import Mathlib\n", proof_nonce="n" * 64)
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (100, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=1")

    result = CliRunner().invoke(main, ["status"])

    assert result.exit_code == 0
    assert "LEMMA_TARGET_GENESIS_BLOCK is required" in result.output
    assert "proof" in result.output
    assert "uncommitted" in result.output
    assert "Next: lemma setup --role miner" in result.output


def test_status_calls_stale_proof_replaceable(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("LEMMA_TARGET_GENESIS_BLOCK", "100")
    problem = resolve_problem(
        LemmaSettings(_env_file=None, miner_submissions_path=store),
        "known/smoke/nat_two_plus_two_eq_four",
    )
    save_pending_submission(store, problem, "import Mathlib\n")
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (130, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=1")

    result = CliRunner().invoke(main, ["status"])

    assert result.exit_code == 0
    assert "stale local proof" in result.output
    assert "Next: lemma mine --replace" in result.output


def test_status_explains_committed_reveal_needs_serving(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "ledger.jsonl"))
    monkeypatch.setenv("LEMMA_TARGET_GENESIS_BLOCK", "100")
    problem = resolve_problem(
        LemmaSettings(_env_file=None, miner_submissions_path=store),
        "known/smoke/nat_two_plus_two_eq_four",
    )
    save_pending_submission(
        store,
        problem,
        "import Mathlib\n",
        proof_nonce="secret",
        commitment_hash="c" * 64,
        commitment_status="committed",
    )
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (130, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=1")

    result = CliRunner().invoke(main, ["status"])

    assert result.exit_code == 0
    assert "committed; reveal open" in result.output
    assert "keep lemma mine running; proof is ready for validator polling" in result.output
    assert "validators poll about every 5 min, then run Lean" in result.output
    assert "https://lemmasub.net/miners/" in result.output
    assert "lemma target ledger (local validator/operator ledger)" in result.output
    assert "Next: lemma mine" in result.output


def test_setup_prints_btcli_commands_and_asks_before_env_write(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LEMMA_TARGET_GENESIS_BLOCK", raising=False)
    monkeypatch.delenv("LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED", raising=False)
    monkeypatch.delenv("LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED", raising=False)
    monkeypatch.setenv("BT_WALLET_COLD", "cold")
    monkeypatch.setenv("BT_WALLET_HOT", "hot")
    monkeypatch.setenv("NETUID", "467")
    monkeypatch.setenv("SUBTENSOR_NETWORK", "test")
    monkeypatch.setattr("lemma.cli.main.shutil.which", lambda name: None)
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (123, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey-address")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "not registered")

    result = CliRunner().invoke(main, ["setup", "--role", "miner"], input="n\n")

    assert result.exit_code == 0
    assert "Lemma setup" in result.output
    assert "uv sync --extra btcli" in result.output
    assert "btcli wallet create --wallet.name cold --wallet.hotkey hot" in result.output
    assert "btcli subnets register --netuid 467" in result.output
    assert "LEMMA_TARGET_GENESIS_BLOCK=123" in result.output
    assert "No .env changes written" in result.output
    assert not (tmp_path / ".env").exists()


def test_setup_hotkey_option_writes_role_specific_env(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LEMMA_TARGET_GENESIS_BLOCK", raising=False)
    monkeypatch.delenv("LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED", raising=False)
    monkeypatch.delenv("LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED", raising=False)
    monkeypatch.setenv("BT_WALLET_COLD", "lemma")
    monkeypatch.setenv("BT_WALLET_HOT", "lemmahot")
    monkeypatch.setattr("lemma.cli.main.shutil.which", lambda name: "/bin/tool")
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (123, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey-address")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=2")

    result = CliRunner().invoke(main, ["setup", "--role", "validator", "--hotkey", "lemmaminer2"], input="n\n")

    assert result.exit_code == 0
    assert "wallet" in result.output
    assert "lemma/lemmaminer2" in result.output
    assert "BT_VALIDATOR_WALLET_HOT=lemmaminer2" in result.output
    assert "No .env changes written" in result.output


def test_setup_refreshes_expired_first_genesis(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_TARGET_GENESIS_BLOCK", "100")
    monkeypatch.delenv("LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED", raising=False)
    monkeypatch.setattr("lemma.cli.main.shutil.which", lambda name: "/bin/tool")
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (130, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey-address")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=1")

    result = CliRunner().invoke(main, ["setup", "--role", "miner"], input="n\n")

    assert result.exit_code == 0
    assert "LEMMA_TARGET_GENESIS_BLOCK=130" in result.output
    assert "No .env changes written" in result.output


def test_setup_auto_retries_commit_after_approved_refresh(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(ledger))
    monkeypatch.setenv("LEMMA_TARGET_GENESIS_BLOCK", "100")
    monkeypatch.delenv("LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED", raising=False)
    problem = resolve_problem(
        LemmaSettings(
            _env_file=None,
            miner_submissions_path=store,
            solved_ledger_path=ledger,
            target_genesis_block=100,
        ),
        "known/smoke/nat_two_plus_two_eq_four",
    )
    save_pending_submission(store, problem, "import Mathlib\n", proof_nonce="secret")
    started: list[int | None] = []
    committed_genesis: list[int | None] = []

    def fake_publish(settings, problem, entry):
        committed_genesis.append(settings.target_genesis_block)
        return replace(entry, commitment_status="committed")

    monkeypatch.setattr("lemma.cli.main.shutil.which", lambda name: "/bin/tool")
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (130, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey-address")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=1")
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", fake_publish)
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(settings.target_genesis_block))

    result = CliRunner().invoke(main, ["setup", "--role", "miner"], input="y\n")

    assert result.exit_code == 0
    assert "Updated .env" in result.output
    assert "Stored proof found. Publishing commitment now." in result.output
    assert "Commitment published. Starting miner." in result.output
    assert "Next:" not in result.output
    assert committed_genesis == [130]
    assert started == [130]
    assert "LEMMA_TARGET_GENESIS_BLOCK=130" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_setup_auto_retries_commit_when_config_is_already_current(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.problems.known_theorems import known_theorems_manifest_sha256
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(ledger))
    monkeypatch.setenv("LEMMA_TARGET_GENESIS_BLOCK", "100")
    monkeypatch.setenv(
        "LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED",
        known_theorems_manifest_sha256(None),
    )
    problem = resolve_problem(
        LemmaSettings(
            _env_file=None,
            miner_submissions_path=store,
            solved_ledger_path=ledger,
            target_genesis_block=100,
        ),
        "known/smoke/nat_two_plus_two_eq_four",
    )
    save_pending_submission(store, problem, "import Mathlib\n", proof_nonce="secret")
    committed: list[int | None] = []
    started: list[int | None] = []

    def fake_publish(settings, problem, entry):
        committed.append(settings.target_genesis_block)
        return replace(entry, commitment_status="committed")

    monkeypatch.setattr("lemma.cli.main.shutil.which", lambda name: "/bin/tool")
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (110, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey-address")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=1")
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", fake_publish)
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(settings.target_genesis_block))

    result = CliRunner().invoke(main, ["setup", "--role", "miner"])

    assert result.exit_code == 0
    assert "No .env changes suggested" not in result.output
    assert "Stored proof found. Publishing commitment now." in result.output
    assert "Commitment published. Starting miner." in result.output
    assert committed == [100]
    assert started == [100]


def test_setup_refreshes_and_retries_when_stored_proof_window_closed(monkeypatch, tmp_path: Path) -> None:
    from lemma.cli.main import CommitWindowClosedError
    from lemma.problems.factory import resolve_problem
    from lemma.problems.known_theorems import known_theorems_manifest_sha256
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(ledger))
    monkeypatch.setenv("LEMMA_TARGET_GENESIS_BLOCK", "100")
    monkeypatch.setenv(
        "LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED",
        known_theorems_manifest_sha256(None),
    )
    problem = resolve_problem(
        LemmaSettings(
            _env_file=None,
            miner_submissions_path=store,
            solved_ledger_path=ledger,
            target_genesis_block=100,
        ),
        "known/smoke/nat_two_plus_two_eq_four",
    )
    save_pending_submission(store, problem, "import Mathlib\n", proof_nonce="secret")
    committed: list[int | None] = []
    started: list[int | None] = []

    def fake_publish(settings, problem, entry):
        committed.append(settings.target_genesis_block)
        if len(committed) == 1:
            raise CommitWindowClosedError("closed", current_block=130, entry=entry)
        return replace(entry, commitment_status="committed")

    monkeypatch.setattr("lemma.cli.main.shutil.which", lambda name: "/bin/tool")
    monkeypatch.setattr("lemma.cli.main._current_block_or_none", lambda settings: (110, None))
    monkeypatch.setattr("lemma.cli.main._wallet_hotkey_address", lambda settings, role="miner": "hotkey-address")
    monkeypatch.setattr("lemma.cli.main._registration_text", lambda settings, hotkey: "registered uid=1")
    monkeypatch.setattr("lemma.cli.main._publish_pending_commitment", fake_publish)
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(settings.target_genesis_block))

    result = CliRunner().invoke(main, ["setup", "--role", "miner"], input="y\n")

    assert result.exit_code == 0
    assert "Commit window closed while this proof was being prepared." in result.output
    assert "Refresh the first target window and retry the commitment now?" in result.output
    assert "Commitment published. Starting miner." in result.output
    assert committed == [100, 130]
    assert started == [130]
    assert "LEMMA_TARGET_GENESIS_BLOCK=130" in (tmp_path / ".env").read_text(encoding="utf-8")


def test_validate_runs_check_before_service_start(monkeypatch) -> None:
    calls: list[str] = []

    class FakeValidatorService:
        def __init__(self, settings, dry_run=None) -> None:
            assert dry_run is False

        def run_blocking(self) -> None:
            calls.append("start")

    monkeypatch.setattr(
        "lemma.cli.validator_check.run_validator_check",
        lambda settings: calls.append("check") or 0,
    )
    monkeypatch.setattr("lemma.validator.service.ValidatorService", FakeValidatorService)

    result = CliRunner().invoke(main, ["validate"])

    assert result.exit_code == 0
    assert calls == ["check", "start"]


def test_validate_hotkey_option_uses_validator_wallet(monkeypatch) -> None:
    seen: list[str | None] = []

    class FakeValidatorService:
        def __init__(self, settings, dry_run=None) -> None:
            seen.append(settings.validator_wallet_hot)
            assert dry_run is False

        def run_blocking(self) -> None:
            seen.append("start")

    def fake_check(settings):
        seen.append(settings.validator_wallet_hot)
        return 0

    monkeypatch.setattr("lemma.cli.validator_check.run_validator_check", fake_check)
    monkeypatch.setattr("lemma.validator.service.ValidatorService", FakeValidatorService)

    result = CliRunner().invoke(main, ["validate", "--hotkey", "lemmaminer2"])

    assert result.exit_code == 0
    assert seen == ["lemmaminer2", "lemmaminer2", "start"]


def test_mine_hotkey_option_uses_miner_wallet(monkeypatch, tmp_path: Path) -> None:
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    store = tmp_path / "submissions.json"
    started: list[str] = []
    monkeypatch.setenv("LEMMA_MINER_SUBMISSIONS_PATH", str(store))
    settings = LemmaSettings(_env_file=None, miner_submissions_path=store)
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    save_pending_submission(store, problem, "import Mathlib\n", proof_nonce="secret", commitment_status="committed")
    monkeypatch.setattr("lemma.cli.main._start_miner", lambda settings: started.append(settings.wallet_hot))

    result = CliRunner().invoke(main, ["mine", "--hotkey", "lemmaminer2"])

    assert result.exit_code == 0
    assert started == ["lemmaminer2"]


def test_publish_pending_commitment_writes_public_chain_payload(monkeypatch, tmp_path: Path) -> None:
    from lemma.cli.main import _publish_pending_commitment
    from lemma.commitments import decode_commitment_payload
    from lemma.problems.factory import resolve_problem
    from lemma.submissions import save_pending_submission

    class FakeSubtensor:
        def __init__(self) -> None:
            self.payload = ""

        def get_current_block(self) -> int:
            return 10

        def set_commitment(self, *, wallet, netuid, data):
            self.payload = str(data)
            return SimpleNamespace(success=True, message="ok")

    fake_subtensor = FakeSubtensor()
    settings = LemmaSettings(
        _env_file=None,
        miner_submissions_path=tmp_path / "submissions.json",
        solved_ledger_path=tmp_path / "ledger.jsonl",
        target_genesis_block=10,
        commit_window_blocks=25,
    )
    problem = resolve_problem(settings, "known/smoke/nat_two_plus_two_eq_four")
    entry = save_pending_submission(settings.miner_submissions_path, problem, "import Mathlib\n", proof_nonce="secret")
    monkeypatch.setattr("lemma.common.subtensor.get_subtensor", lambda settings: fake_subtensor)
    monkeypatch.setattr(
        "bittensor.Wallet",
        lambda *args, **kwargs: SimpleNamespace(hotkey=SimpleNamespace(ss58_address="miner-hotkey")),
    )

    updated = _publish_pending_commitment(settings, problem, entry)
    payload = decode_commitment_payload(fake_subtensor.payload)

    assert updated.commitment_status == "committed"
    assert updated.committed_hotkey == "miner-hotkey"
    assert updated.committed_block == 10
    assert payload is not None
    assert len(fake_subtensor.payload.encode()) <= 128
    assert payload["commitment_hash"] == updated.commitment_hash
    assert "miner_hotkey" not in payload
    assert "target_id" not in payload
    assert "proof_sha256" not in payload
    assert "nonce" not in payload
    assert "proof_script" not in fake_subtensor.payload


def _committed_entry(settings, problem, entry):
    return replace(
        entry,
        commitment_status="committed",
        commitment_hash="c" * 64,
        committed_block=10,
        commit_cutoff_block=34,
        reveal_block=35,
    )


def _proof_file(tmp_path: Path) -> Path:
    proof = tmp_path / "Submission.lean"
    proof.write_text(
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        "theorem nat_two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by\n"
        "  rfl\n\n"
        "end Submission\n",
        encoding="utf-8",
    )
    return proof


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


def test_dashboard_help_lists_export_command() -> None:
    result = CliRunner().invoke(main, ["dashboard", "--help"])

    assert result.exit_code == 0
    assert "export" in result.output


def test_portal_help_lists_start_command() -> None:
    result = CliRunner().invoke(main, ["portal", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output


def test_validator_help_lists_proof_subcommands() -> None:
    result = CliRunner().invoke(main, ["validator", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output
    assert "dry-run" in result.output
    assert "check" in result.output
    assert "config" not in result.output


def test_target_command_shows_active_known_theorem(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "solved-ledger.jsonl"))

    result = CliRunner().invoke(main, ["target", "show"])

    assert result.exit_code == 0
    assert "Lemma target" in result.output
    assert "known/smoke/nat_two_plus_two_eq_four" in result.output
    assert "proof_reference=" in result.output


def test_target_ledger_empty(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(tmp_path / "solved-ledger.jsonl"))

    result = CliRunner().invoke(main, ["target", "ledger"])

    assert result.exit_code == 0
    assert "No solved targets yet." in result.output


def test_target_ledger_shows_solver_uids_and_proofs(monkeypatch, tmp_path: Path) -> None:
    import json

    ledger = tmp_path / "solved-ledger.jsonl"
    ledger.write_text(
        json.dumps(
            {
                "target_id": "known/test/one",
                "solvers": [
                    {
                        "uid": 2,
                        "hotkey": "hk2",
                        "coldkey": "ck2",
                        "proof_sha256": "a" * 64,
                        "commitment_hash": "c" * 64,
                        "verify_reason": "ok",
                        "build_seconds": 1.0,
                    },
                    {
                        "uid": 3,
                        "hotkey": "hk3",
                        "coldkey": "ck3",
                        "proof_sha256": "b" * 64,
                        "commitment_hash": "d" * 64,
                        "verify_reason": "ok",
                        "build_seconds": 1.0,
                    },
                ],
                "accepted_block": 55,
                "accepted_unix": 1,
                "validator_hotkey": "validator",
                "lemma_version": "0.1.0",
                "theorem_statement_sha256": "c" * 64,
            },
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LEMMA_LEDGER_PATH", str(ledger))

    result = CliRunner().invoke(main, ["target", "ledger"])

    assert result.exit_code == 0
    assert "known/test/one" in result.output
    assert "solver_uid(s)" in result.output
    assert "2,3" in result.output
    assert "aaaaaaaaaaaaaaaa" in result.output
    assert "bbbbbbbbbbbbbbbb" in result.output
    assert "cccccccccccccccc" in result.output
    assert "dddddddddddddddd" in result.output
    assert "55" in result.output
