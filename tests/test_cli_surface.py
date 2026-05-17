"""Core CLI command surface."""

import hashlib
import json

import lemma.cli.main as cli_main
import pytest
from click.testing import CliRunner
from lemma.cli.main import main

PUBLIC_COMMANDS = ("setup", "mine", "status", "validate")
HIDDEN_ALIASES = (
    "config",
    "theorem",
    "proof",
    "miner",
    "validator",
    "bounty",
    "configure",
    "doctor",
    "preview",
    "problems",
    "verify",
    "meta",
    "lean-worker",
)


def _commands_from_help(output: str) -> list[str]:
    return [
        line.strip().split()[0]
        for line in output.split("Commands:", 1)[1].splitlines()
        if line.startswith("  ")
    ]


def test_home_screen_lists_grouped_commands() -> None:
    result = CliRunner().invoke(main)

    assert result.exit_code == 0
    commands = _commands_from_help(result.output)
    assert commands == list(PUBLIC_COMMANDS)
    for command in HIDDEN_ALIASES:
        assert command not in commands


def test_help_lists_grouped_commands() -> None:
    result = CliRunner().invoke(main, ["--help"])

    assert result.exit_code == 0
    assert _commands_from_help(result.output) == list(PUBLIC_COMMANDS)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (("setup", "--help"), "--role"),
        (("mine", "--help"), "--claimant-evm"),
        (("status", "--help"), "escrow-backed"),
        (("validate", "--help"), "--once"),
    ],
)
def test_visible_group_help(command: tuple[str, ...], expected: str) -> None:
    result = CliRunner().invoke(main, command)

    assert result.exit_code == 0
    assert expected in result.output


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (("configure", "--help"), "subnet-pins"),
        (("config", "--help"), "subnet-pins"),
        (("doctor", "--help"), "Check local environment"),
        (("lean-worker", "--help"), "Compatibility alias"),
        (("meta", "--help"), "Compatibility alias"),
        (("miner", "--help"), "observability"),
        (("preview", "--help"), "--no-verify"),
        (("proof", "--help"), "preview"),
        (("problems", "--help"), "show"),
        (("theorem", "--help"), "current"),
        (("validator", "--help"), "lean-worker"),
        (("verify", "--help"), "--submission"),
        (("bounty", "--help"), "submit"),
    ],
)
def test_hidden_aliases_still_work(command: tuple[str, ...], expected: str) -> None:
    result = CliRunner().invoke(main, command)

    assert result.exit_code == 0
    assert expected in result.output


def test_setup_defaults_to_miner(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_setup(env_path, role: str) -> None:
        calls.append((env_path.name, role))

    import lemma.cli.env_wizard as env_wizard

    monkeypatch.setattr(env_wizard, "run_setup", fake_setup)
    result = CliRunner().invoke(main, ["setup"])

    assert result.exit_code == 0
    assert calls == [(".env", "miner")]


def test_miner_check_runs_preflight_without_starting(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    monkeypatch.setattr(cli_main, "_maybe_run_setup_for_missing_env", lambda role: events.append(("setup", role)))
    monkeypatch.setattr(
        cli_main,
        "_run_miner_preflight",
        lambda settings, start_after: events.append(
            ("preflight", (settings.wallet_hot, settings.axon_port, start_after))
        )
        or 0,
    )
    monkeypatch.setattr(cli_main, "_miner_run_axon", lambda settings, cap: events.append(("start", cap)))

    result = CliRunner().invoke(main, ["miner", "check", "--hotkey", "second", "--port", "8092"])

    assert result.exit_code == 0
    assert events == [("setup", "miner"), ("preflight", ("second", 8092, False))]


def test_miner_start_runs_preflight_then_starts_with_overrides(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    monkeypatch.setattr(cli_main, "_maybe_run_setup_for_missing_env", lambda role: events.append(("setup", role)))
    monkeypatch.setattr(
        cli_main,
        "_run_miner_preflight",
        lambda settings, start_after: events.append(
            ("preflight", (settings.wallet_hot, settings.axon_port, start_after))
        )
        or 0,
    )
    monkeypatch.setattr(cli_main, "_miner_run_axon", lambda settings, cap: events.append(("start", cap)))

    result = CliRunner().invoke(
        main,
        ["miner", "start", "--hotkey", "second", "--port", "8092", "--max-forwards-per-day", "5"],
    )

    assert result.exit_code == 0
    assert events == [
        ("setup", "miner"),
        ("preflight", ("second", 8092, True)),
        ("start", 5),
    ]


def test_public_mine_without_bounty_lists_registry(monkeypatch, tmp_path) -> None:
    raw = json.dumps(
        {
            "schema_version": 2,
            "bounties": [
                {
                    "id": "fc.test",
                    "title": "Test bounty",
                    "status": "candidate",
                    "source": {"name": "Formal Conjectures"},
                    "problem": {
                        "id": "fc.test",
                        "theorem_name": "test_theorem",
                        "type_expr": "True",
                        "split": "bounty",
                        "lean_toolchain": "leanprover/lean4:v4.15.0",
                        "mathlib_rev": "abc123",
                        "imports": ["Mathlib"],
                        "extra": {"informal_statement": "Prove True."},
                    },
                }
            ],
        },
        sort_keys=True,
    ).encode()
    registry_path = tmp_path / "registry.json"
    registry_path.write_bytes(raw)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_URL", str(registry_path))
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED", hashlib.sha256(raw).hexdigest())

    result = CliRunner().invoke(main, ["mine"])

    assert result.exit_code == 0
    assert "Lemma mine" in result.output
    assert "Draft candidates" in result.output


def test_validator_check_runs_preflight_without_starting(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    monkeypatch.setattr(cli_main, "_maybe_run_setup_for_missing_env", lambda role: events.append(("setup", role)))
    monkeypatch.setattr(
        cli_main,
        "_run_validator_preflight",
        lambda start_after, dry_run=False: events.append(("preflight", (start_after, dry_run))) or 0,
    )
    monkeypatch.setattr(cli_main, "_validator_run_blocking", lambda dry_run: events.append(("start", dry_run)))

    result = CliRunner().invoke(main, ["validator", "check"])

    assert result.exit_code == 0
    assert events == [("setup", "validator"), ("preflight", (False, False))]


def test_validator_dry_run_starts_after_preflight(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    monkeypatch.setattr(cli_main, "_maybe_run_setup_for_missing_env", lambda role: events.append(("setup", role)))
    monkeypatch.setattr(
        cli_main,
        "_run_validator_preflight",
        lambda start_after, dry_run=False: events.append(("preflight", (start_after, dry_run))) or 0,
    )
    monkeypatch.setattr(cli_main, "_validator_run_blocking", lambda dry_run: events.append(("start", dry_run)))

    result = CliRunner().invoke(main, ["validator", "dry-run"])

    assert result.exit_code == 0
    assert events == [("setup", "validator"), ("preflight", (True, True)), ("start", True)]


def test_validate_cadence_flag_dispatches_to_validator_flow(monkeypatch) -> None:
    events: list[tuple[str, object]] = []

    monkeypatch.setattr(cli_main, "_maybe_run_setup_for_missing_env", lambda role: events.append(("setup", role)))
    monkeypatch.setattr(
        cli_main,
        "_run_validator_preflight",
        lambda start_after, dry_run=False: events.append(("preflight", (start_after, dry_run))) or 0,
    )
    monkeypatch.setattr(cli_main, "_validator_run_blocking", lambda dry_run: events.append(("start", dry_run)))

    result = CliRunner().invoke(main, ["validate", "--cadence", "--dry-run"])

    assert result.exit_code == 0
    assert events == [("setup", "validator"), ("preflight", (True, True)), ("start", True)]


def test_removed_legacy_aliases_fail() -> None:
    legacy_commands = [
        ("try" + "-prover",),
        ("rehear" + "sal",),
        ("validator" + "-check",),
        ("validator", "judge" + "-attest-serve"),
    ]

    for command in legacy_commands:
        result = CliRunner().invoke(main, [*command, "--help"])
        assert result.exit_code != 0
        assert "No such command" in result.output


@pytest.mark.parametrize("command", [("validator", "lean-worker"), ("lean-worker",)])
def test_lean_worker_rejects_public_bind_without_bearer(monkeypatch, tmp_path, command: tuple[str, ...]) -> None:
    monkeypatch.delenv("LEMMA_LEAN_VERIFY_REMOTE_BEARER", raising=False)
    monkeypatch.delenv("LEMMA_LEAN_WORKER_ALLOW_UNAUTHENTICATED_NON_LOOPBACK", raising=False)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(main, [*command, "--host", "0.0.0.0"])

    assert result.exit_code != 0
    assert "refuses unauthenticated non-loopback binds" in result.output
