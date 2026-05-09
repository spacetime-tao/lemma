"""LemmaSettings prefers `.env` over process environment (unless LEMMA_PREFER_PROCESS_ENV)."""

from __future__ import annotations

import pytest
from lemma.common.config import CANONICAL_JUDGE_OPENAI_MODEL, LemmaSettings


def test_dotenv_beats_process_env_for_openai_model(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f'OPENAI_MODEL="{CANONICAL_JUDGE_OPENAI_MODEL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "legacy/from-shell")
    s = LemmaSettings(_env_file=str(env_file))
    assert s.openai_model == CANONICAL_JUDGE_OPENAI_MODEL


def test_process_env_beats_dotenv_when_flag(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LEMMA_PREFER_PROCESS_ENV", "1")
    env_file = tmp_path / ".env"
    env_file.write_text(f'OPENAI_MODEL="{CANONICAL_JUDGE_OPENAI_MODEL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "legacy/from-shell")
    s = LemmaSettings(_env_file=str(env_file))
    assert s.openai_model == "legacy/from-shell"


def test_dotenv_sets_lean_use_docker(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    monkeypatch.delenv("LEMMA_USE_DOCKER", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LEMMA_USE_DOCKER=false\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.lean_use_docker is False


def test_explicit_init_kwarg_beats_all(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f'OPENAI_MODEL="{CANONICAL_JUDGE_OPENAI_MODEL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "legacy/from-shell")
    s = LemmaSettings(_env_file=str(env_file), openai_model="explicit")
    assert s.openai_model == "explicit"


def test_documented_validator_wallet_env_overrides_miner_wallet(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "BT_WALLET_COLD=miner-cold",
                "BT_WALLET_HOT=miner-hot",
                "BT_VALIDATOR_WALLET_COLD=validator-cold",
                "BT_VALIDATOR_WALLET_HOT=validator-hot",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.validator_wallet_names() == ("validator-cold", "validator-hot")


def test_documented_protocol_env_names_work(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LEMMA_COMMIT_REVEAL_ENABLED=1",
                "LEMMA_MINER_VERIFY_ATTEST_ENABLED=1",
                "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION=0.25",
                "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT=salt",
                "LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1",
                "LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS=http://peer/lemma/judge_profile_sha256",
                "LEMMA_JUDGE_PROFILE_ATTEST_SKIP=1",
                "LEMMA_JUDGE_PROFILE_ATTEST_HTTP_TIMEOUT_S=3",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.lemma_commit_reveal_enabled is True
    assert s.lemma_miner_verify_attest_enabled is True
    assert s.lemma_miner_verify_attest_spot_verify_fraction == 0.25
    assert s.lemma_miner_verify_attest_spot_verify_salt == "salt"
    assert s.lemma_judge_profile_attest_enabled is True
    assert s.lemma_judge_profile_attest_peer_urls == "http://peer/lemma/judge_profile_sha256"
    assert s.lemma_judge_profile_attest_allow_skip is True
    assert s.lemma_judge_profile_attest_http_timeout_s == 3.0
