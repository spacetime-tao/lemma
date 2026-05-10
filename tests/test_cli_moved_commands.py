"""Compatibility hints for commands moved to lemma-cli."""

from click.testing import CliRunner
from lemma.cli.main import main


def test_moved_top_level_command_forwards_args_to_lemma_cli() -> None:
    result = CliRunner().invoke(main, ["doctor", "--quick"])

    assert result.exit_code == 0
    assert "Doctor moved to lemma-cli." in result.output
    assert "Run `lemma-cli doctor --quick`." in result.output
    assert "lemma validator start" in result.output


def test_moved_configure_command_forwards_args_to_lemma_cli() -> None:
    result = CliRunner().invoke(main, ["configure", "judge", "--model", "demo"])

    assert result.exit_code == 0
    assert "Run `lemma-cli configure judge --model demo`." in result.output


def test_moved_configure_group_lists_topics() -> None:
    result = CliRunner().invoke(main, ["configure"])

    assert result.exit_code == 0
    assert "Run `lemma-cli configure`." in result.output
    assert "Core commands still live here" in result.output


def test_moved_miner_observability_command_points_to_lemma_cli() -> None:
    result = CliRunner().invoke(main, ["miner", "observability"])

    assert result.exit_code == 0
    assert "Miner observability moved to lemma-cli." in result.output
    assert "Run `lemma-cli miner-observability`." in result.output


def test_moved_status_command_points_to_lemma_cli() -> None:
    result = CliRunner().invoke(main, ["status"])

    assert result.exit_code == 0
    assert "Status view moved to lemma-cli." in result.output
    assert "Run `lemma-cli status`." in result.output


def test_moved_problems_command_forwards_args_to_lemma_cli() -> None:
    result = CliRunner().invoke(main, ["problems", "show", "--current"])

    assert result.exit_code == 0
    assert "Problem inspector moved to lemma-cli." in result.output
    assert "Run `lemma-cli problems show --current`." in result.output


def test_moved_judge_command_forwards_args_to_lemma_cli() -> None:
    result = CliRunner().invoke(main, ["judge", "--trace", "trace.txt"])

    assert result.exit_code == 0
    assert "Judge preview moved to lemma-cli." in result.output
    assert "Run `lemma-cli judge --trace trace.txt`." in result.output


def test_moved_validator_config_command_points_to_lemma_cli() -> None:
    result = CliRunner().invoke(main, ["validator", "config"])

    assert result.exit_code == 0
    assert "Validator config moved to lemma-cli." in result.output
    assert "Run `lemma-cli validator-config`." in result.output
