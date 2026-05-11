"""Core CLI command surface."""

from click.testing import CliRunner
from lemma.cli.main import main


def test_home_screen_lists_core_commands() -> None:
    result = CliRunner().invoke(main)

    assert result.exit_code == 0
    assert "lemma setup" in result.output
    assert "lemma doctor" in result.output
    assert "lemma preview" in result.output
    assert "lemma miner start" in result.output
    assert "lemma validator start" in result.output


def test_setup_command_is_local() -> None:
    result = CliRunner().invoke(main, ["setup", "--help"])

    assert result.exit_code == 0
    assert "--role" in result.output


def test_preview_command_is_public() -> None:
    result = CliRunner().invoke(main, ["preview", "--help"])

    assert result.exit_code == 0
    assert "--no-verify" in result.output
    assert "--retry-attempts" in result.output


def test_miner_help_lists_local_subcommands() -> None:
    result = CliRunner().invoke(main, ["miner", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output
    assert "dry-run" in result.output
    assert "observability" in result.output


def test_validator_help_lists_local_subcommands() -> None:
    result = CliRunner().invoke(main, ["validator", "--help"])

    assert result.exit_code == 0
    assert "start" in result.output
    assert "dry-run" in result.output
    assert "check" in result.output
    assert "config" in result.output


def test_configure_group_lists_public_topics() -> None:
    result = CliRunner().invoke(main, ["configure", "--help"])

    assert result.exit_code == 0
    assert "subnet-pins" in result.output
    assert "prover" in result.output
    assert "judge" not in result.output


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
