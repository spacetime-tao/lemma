"""LemmaSettings keeps the target/custody env surface small."""

from __future__ import annotations

import pytest
from lemma.common.config import LemmaSettings


def test_dotenv_beats_process_env_for_registry_url(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text('LEMMA_BOUNTY_REGISTRY_URL="from-dotenv.json"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_BOUNTY_REGISTRY_URL", "from-process.json")

    s = LemmaSettings(_env_file=str(env_file))

    assert s.bounty_registry_url == "from-dotenv.json"


def test_process_env_beats_dotenv_when_flag(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LEMMA_PREFER_PROCESS_ENV", "1")
    env_file = tmp_path / ".env"
    env_file.write_text('LEMMA_BOUNTY_EVM_RPC_URL="https://dotenv.example"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LEMMA_BOUNTY_EVM_RPC_URL", "https://process.example")

    s = LemmaSettings(_env_file=str(env_file))

    assert s.bounty_evm_rpc_url == "https://process.example"


def test_lowercase_field_env_aliases_are_ignored(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "bounty_registry_url=lowercase-env",
                "lean_use_docker=false",
                "wallet_cold=lowercase-cold",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    s = LemmaSettings(_env_file=str(env_file))

    assert s.bounty_registry_url == LemmaSettings.model_fields["bounty_registry_url"].default
    assert s.lean_use_docker is True
    assert s.wallet_cold == "default"


def test_constructor_field_names_still_work() -> None:
    s = LemmaSettings(
        _env_file=None,
        bounty_registry_url="explicit.json",
        lean_use_docker=False,
        wallet_cold="cold",
        wallet_hot="hot",
    )

    assert s.bounty_registry_url == "explicit.json"
    assert s.lean_use_docker is False
    assert s.wallet_cold == "cold"
    assert s.wallet_hot == "hot"


def test_bounty_escrow_env_names_work(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LEMMA_BOUNTY_REWARD_CUSTODY=evm_escrow",
                "LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED=" + ("a" * 64),
                "LEMMA_BOUNTY_HTTP_TIMEOUT_S=5",
                "LEMMA_BOUNTY_EVM_RPC_URL=https://rpc.example",
                "LEMMA_BOUNTY_EVM_CHAIN_ID=945",
                "LEMMA_BOUNTY_ESCROW_CONTRACT_ADDRESS=0x" + ("b" * 40),
                "BT_WALLET_COLD=cold",
                "BT_WALLET_HOT=hot",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    s = LemmaSettings(_env_file=str(env_file))

    assert s.bounty_reward_custody == "evm_escrow"
    assert s.bounty_registry_sha256_expected == "a" * 64
    assert s.bounty_http_timeout_s == 5
    assert s.bounty_evm_rpc_url == "https://rpc.example"
    assert s.bounty_evm_chain_id == 945
    assert s.bounty_escrow_contract_address == "0x" + ("b" * 40)
    assert (s.wallet_cold, s.wallet_hot) == ("cold", "hot")


def test_lean_workspace_cache_defaults_and_env(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            [
                "LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS=0",
                "LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES=12345",
                "LEMMA_LEAN_VERIFY_REMOTE_TIMEOUT_MARGIN_S=7",
            ],
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    defaults = LemmaSettings(_env_file=None)
    s = LemmaSettings(_env_file=str(env_file))

    assert defaults.lemma_lean_workspace_cache_max_dirs == 8
    assert s.lemma_lean_workspace_cache_max_dirs == 0
    assert s.lemma_lean_workspace_cache_max_bytes == 12345
    assert s.lean_verify_remote_timeout_margin_s == 7


def test_lean_worker_dev_override_env_name_works(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LEMMA_LEAN_WORKER_ALLOW_UNAUTHENTICATED_NON_LOOPBACK=1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    s = LemmaSettings(_env_file=str(env_file))

    assert s.lean_worker_allow_unauthenticated_non_loopback is True
