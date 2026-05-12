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


def test_public_ip_discovery_is_opt_in_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AXON_DISCOVER_EXTERNAL_IP", raising=False)
    s = LemmaSettings(_env_file=None)
    assert s.axon_discover_external_ip is False


def test_documented_public_ip_discovery_env_enables_lookup(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("AXON_DISCOVER_EXTERNAL_IP=true\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.axon_discover_external_ip is True


def test_explicit_init_kwarg_beats_all(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f'OPENAI_MODEL="{CANONICAL_JUDGE_OPENAI_MODEL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "legacy/from-shell")
    s = LemmaSettings(_env_file=str(env_file), openai_model="explicit")
    assert s.openai_model == "explicit"


def test_lowercase_field_env_aliases_are_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "openai_model=lowercase-env",
                "lean_use_docker=false",
                "miner_max_concurrent_forwards=99",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.openai_model == CANONICAL_JUDGE_OPENAI_MODEL
    assert s.lean_use_docker is True
    assert s.miner_max_concurrent_forwards == 8


def test_constructor_field_names_still_work() -> None:
    s = LemmaSettings(
        _env_file=None,
        openai_model="explicit",
        lean_use_docker=False,
        miner_max_concurrent_forwards=3,
    )
    assert s.openai_model == "explicit"
    assert s.lean_use_docker is False
    assert s.miner_max_concurrent_forwards == 3


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
                "LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED=1",
                "LEMMA_VALIDATOR_PROFILE_ATTEST_PEER_URLS=http://peer/lemma/validator_profile_sha256",
                "LEMMA_VALIDATOR_PROFILE_ATTEST_SKIP=1",
                "LEMMA_VALIDATOR_PROFILE_ATTEST_HTTP_TIMEOUT_S=3",
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
    assert s.lemma_judge_profile_attest_peer_urls == "http://peer/lemma/validator_profile_sha256"
    assert s.lemma_judge_profile_attest_allow_skip is True
    assert s.lemma_judge_profile_attest_http_timeout_s == 3.0


def test_legacy_judge_profile_attest_aliases_still_work(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
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
    assert s.lemma_judge_profile_attest_enabled is True
    assert s.lemma_judge_profile_attest_peer_urls == "http://peer/lemma/judge_profile_sha256"
    assert s.lemma_judge_profile_attest_allow_skip is True
    assert s.lemma_judge_profile_attest_http_timeout_s == 3.0


def test_documented_timeout_and_prover_policy_env_names_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LEMMA_TIMEOUT_SCALE_BY_SPLIT=1",
                "LEMMA_TIMEOUT_SPLIT_EASY_MULT=1.1",
                "LEMMA_TIMEOUT_SPLIT_MEDIUM_MULT=1.2",
                "LEMMA_TIMEOUT_SPLIT_HARD_MULT=1.3",
                "LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS=500",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.timeout_scale_by_split is True
    assert s.timeout_split_easy_mult == 1.1
    assert s.timeout_split_medium_mult == 1.2
    assert s.timeout_split_hard_mult == 1.3
    assert s.prover_min_proof_script_chars == 500


def test_hybrid_problem_supply_env_names_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LEMMA_PROBLEM_SOURCE=hybrid",
                "LEMMA_HYBRID_GENERATED_WEIGHT=55",
                "LEMMA_HYBRID_CATALOG_WEIGHT=45",
                "LEMMA_PROBLEM_SUPPLY_REGISTRY_SHA256_EXPECTED=" + ("a" * 64),
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.problem_source == "hybrid"
    assert s.lemma_hybrid_generated_weight == 55
    assert s.lemma_hybrid_catalog_weight == 45
    assert s.problem_supply_registry_expected_sha256 == "a" * 64


def test_documented_lean_worker_dev_override_env_name_works(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LEMMA_LEAN_WORKER_ALLOW_UNAUTHENTICATED_NON_LOOPBACK=1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.lean_worker_allow_unauthenticated_non_loopback is True


def test_undocumented_prover_policy_aliases_are_ignored(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "PROVER_MAX_TOKENS=4096",
                "PROVER_LLM_RETRY_ATTEMPTS=9",
                "PROVER_TEMPERATURE=1.7",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.prover_max_tokens == 32_768
    assert s.prover_llm_retry_attempts == 4
    assert s.prover_temperature == 0.3


def test_documented_miner_observability_env_names_work(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LEMMA_MINER_FORWARD_SUMMARY=false",
                "LEMMA_MINER_FORWARD_TIMELINE=true",
                "LEMMA_MINER_LOG_FORWARDS=true",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.miner_forward_summary is False
    assert s.miner_forward_timeline is True
    assert s.miner_log_forwards is True
