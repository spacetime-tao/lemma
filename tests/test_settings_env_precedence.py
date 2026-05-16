"""LemmaSettings prefers `.env` over process environment unless asked otherwise."""

from __future__ import annotations

from pathlib import Path

import pytest
from lemma.common.config import LemmaSettings


def _settings_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, text: str) -> LemmaSettings:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(text, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return LemmaSettings(_env_file=str(env_file))


def test_dotenv_beats_process_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NETUID", "999")

    s = _settings_from_env(tmp_path, monkeypatch, "NETUID=467\n")

    assert s.netuid == 467


def test_process_env_beats_dotenv_when_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LEMMA_PREFER_PROCESS_ENV", "1")
    monkeypatch.setenv("NETUID", "999")
    env_file = tmp_path / ".env"
    env_file.write_text("NETUID=467\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    s = LemmaSettings(_env_file=str(env_file))

    assert s.netuid == 999


def test_explicit_init_kwarg_beats_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("NETUID", "999")
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("NETUID=467\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    s = LemmaSettings(_env_file=str(env_file), netuid=123)

    assert s.netuid == 123


def test_constructor_field_names_still_work() -> None:
    s = LemmaSettings(
        _env_file=None,
        lean_use_docker=False,
        validator_poll_interval_s=17,
        validator_abort_if_not_registered=False,
    )

    assert s.lean_use_docker is False
    assert s.validator_poll_interval_s == 17
    assert s.validator_abort_if_not_registered is False


def test_lowercase_field_env_aliases_are_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings_from_env(
        tmp_path,
        monkeypatch,
        "\n".join(
            [
                "netuid=999",
                "lean_use_docker=false",
                "validator_poll_interval_s=17",
            ],
        ),
    )

    assert s.netuid == 0
    assert s.lean_use_docker is True
    assert s.validator_poll_interval_s == 300.0


def test_documented_validator_wallet_env_overrides_miner_wallet(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    s = _settings_from_env(
        tmp_path,
        monkeypatch,
        "\n".join(
            [
                "BT_WALLET_COLD=miner-cold",
                "BT_WALLET_HOT=miner-hot",
                "BT_VALIDATOR_WALLET_COLD=validator-cold",
                "BT_VALIDATOR_WALLET_HOT=validator-hot",
            ],
        ),
    )

    assert s.validator_wallet_names() == ("validator-cold", "validator-hot")


def test_documented_proof_env_names_work(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings_from_env(
        tmp_path,
        monkeypatch,
        "\n".join(
            [
                "LEMMA_VALIDATOR_POLL_INTERVAL_S=123",
                "LEMMA_VALIDATOR_POLL_TIMEOUT_S=7",
                "LEMMA_LEDGER_PATH=/tmp/solved-ledger.jsonl",
                "LEMMA_MINER_SUBMISSIONS_PATH=/tmp/submissions.json",
                "LEMMA_CAMPAIGN_ACCEPTANCE_LEDGER_PATH=/tmp/campaign-acceptance.jsonl",
                "LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED=" + ("a" * 64),
                "LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED=" + ("b" * 64),
                "LEMMA_TARGET_GENESIS_BLOCK=1000",
                "LEMMA_COMMIT_WINDOW_BLOCKS=25",
                "LEMMA_PROVER_API_KEY=secret",
                "LEMMA_PROVER_BASE_URL=https://provider.example/v1",
                "LEMMA_PROVER_MODEL=lean-agent",
            ],
        ),
    )

    assert s.validator_poll_interval_s == 123
    assert s.validator_poll_timeout_s == 7
    assert str(s.solved_ledger_path) == "/tmp/solved-ledger.jsonl"
    assert str(s.miner_submissions_path) == "/tmp/submissions.json"
    assert str(s.campaign_acceptance_ledger_path) == "/tmp/campaign-acceptance.jsonl"
    assert s.known_theorems_manifest_expected_sha256 == "a" * 64
    assert s.validator_profile_expected_sha256 == "b" * 64
    assert s.target_genesis_block == 1000
    assert s.commit_window_blocks == 25
    assert s.prover_api_key == "secret"
    assert s.prover_base_url == "https://provider.example/v1"
    assert s.prover_model == "lean-agent"


def test_unknown_ledger_env_name_is_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings_from_env(
        tmp_path,
        monkeypatch,
        "LEMMA_OLD_LEDGER_PATH=/tmp/old-solved-ledger.jsonl\n",
    )

    assert s.solved_ledger_path is None


def test_removed_legacy_env_names_are_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    s = _settings_from_env(
        tmp_path,
        monkeypatch,
        "\n".join(
            [
                "LEMMA_COMMIT_REVEAL_ENABLED=1",
                "LEMMA_MINER_VERIFY_ATTEST_ENABLED=1",
                "LEMMA_SCORING_ROLLING_ALPHA=0.5",
                "PROVER_MODEL=whatever",
            ],
        ),
    )

    assert not hasattr(s, "lemma_commit_reveal_enabled")
    assert not hasattr(s, "lemma_miner_verify_attest_enabled")
    assert s.lemma_scoring_rolling_alpha == 0.5
    assert s.prover_model is None
