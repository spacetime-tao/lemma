"""Environment-driven settings for the proof-only trunk."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource


class LemmaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=False,
    )

    def __init__(self, **data: Any) -> None:
        """Accept Python field-name kwargs without accepting field-name env vars."""
        for name, field in type(self).model_fields.items():
            if name not in data:
                continue
            alias = field.validation_alias
            if isinstance(alias, str):
                data.setdefault(alias, data[name])
                data.pop(name)
        super().__init__(**data)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        if os.environ.get("LEMMA_PREFER_PROCESS_ENV", "").strip().lower() in {"1", "true", "yes"}:
            return (init_settings, env_settings, dotenv_settings, file_secret_settings)
        return (init_settings, dotenv_settings, env_settings, file_secret_settings)

    netuid: int = Field(default=0, ge=0, validation_alias="NETUID")
    problem_source: Literal["known_theorems"] = Field(default="known_theorems", validation_alias="LEMMA_PROBLEM_SOURCE")
    known_theorems_manifest_path: Path | None = Field(
        default=None,
        validation_alias="LEMMA_KNOWN_THEOREMS_MANIFEST_PATH",
    )
    known_theorems_manifest_expected_sha256: str | None = Field(
        default=None,
        validation_alias="LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED",
    )
    solved_ledger_path: Path | None = Field(default=None, validation_alias="LEMMA_LEDGER_PATH")
    miner_submissions_path: Path | None = Field(default=None, validation_alias="LEMMA_MINER_SUBMISSIONS_PATH")

    subtensor_network: str = Field(default="finney", validation_alias="SUBTENSOR_NETWORK")
    subtensor_chain_endpoint: str | None = Field(default=None, validation_alias="SUBTENSOR_CHAIN_ENDPOINT")

    wallet_cold: str = Field(default="default", validation_alias="BT_WALLET_COLD")
    wallet_hot: str = Field(default="default", validation_alias="BT_WALLET_HOT")
    validator_wallet_cold: str | None = Field(default=None, validation_alias="BT_VALIDATOR_WALLET_COLD")
    validator_wallet_hot: str | None = Field(default=None, validation_alias="BT_VALIDATOR_WALLET_HOT")

    axon_port: int = Field(default=8091, validation_alias="AXON_PORT")
    axon_external_ip: str | None = Field(default=None, validation_alias="AXON_EXTERNAL_IP")

    lean_sandbox_image: str = Field(default="lemma/lean-sandbox:latest", validation_alias="LEAN_SANDBOX_IMAGE")
    lean_sandbox_cpu: float = Field(default=2.0, validation_alias="LEAN_SANDBOX_CPU")
    lean_sandbox_mem_mb: int = Field(default=8192, validation_alias="LEAN_SANDBOX_MEM_MB")
    lean_sandbox_network: str = Field(default="none", validation_alias="LEAN_SANDBOX_NETWORK")
    lean_use_docker: bool = Field(default=True, validation_alias="LEMMA_USE_DOCKER")
    allow_host_lean: bool = Field(default=False, validation_alias="LEMMA_ALLOW_HOST_LEAN")
    lean_verify_timeout_s: int = Field(default=300, validation_alias="LEAN_VERIFY_TIMEOUT_S")
    lean_verify_workspace_cache_dir: Path | None = Field(
        default=None,
        validation_alias="LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR",
    )
    lemma_lean_verify_max_concurrent: int = Field(default=4, ge=1, validation_alias="LEMMA_LEAN_VERIFY_MAX_CONCURRENT")
    lemma_lean_workspace_cache_max_dirs: int = Field(
        default=8,
        ge=0,
        validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS",
    )
    lemma_lean_workspace_cache_max_bytes: int = Field(
        default=16 * 1024 * 1024 * 1024,
        ge=0,
        validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES",
    )
    validator_profile_expected_sha256: str | None = Field(
        default=None,
        validation_alias="LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED",
    )
    validator_poll_interval_s: float = Field(
        default=300.0,
        ge=1.0,
        validation_alias="LEMMA_VALIDATOR_POLL_INTERVAL_S",
    )
    validator_poll_timeout_s: float = Field(default=30.0, ge=1.0, validation_alias="LEMMA_VALIDATOR_POLL_TIMEOUT_S")
    target_genesis_block: int | None = Field(default=None, ge=0, validation_alias="LEMMA_TARGET_GENESIS_BLOCK")
    commit_window_blocks: int = Field(default=25, ge=1, validation_alias="LEMMA_COMMIT_WINDOW_BLOCKS")
    validator_abort_if_not_registered: bool = Field(
        default=True,
        validation_alias="LEMMA_VALIDATOR_ABORT_IF_NOT_REGISTERED",
    )
    validator_min_free_bytes: int = Field(
        default=1024 * 1024 * 1024,
        ge=0,
        validation_alias="LEMMA_VALIDATOR_MIN_FREE_BYTES",
    )
    set_weights_max_retries: int = Field(default=3, ge=1, validation_alias="LEMMA_SET_WEIGHTS_MAX_RETRIES")
    set_weights_retry_delay_s: float = Field(default=2.0, ge=0.0, validation_alias="LEMMA_SET_WEIGHTS_RETRY_DELAY_S")
    public_dashboard_url: str = Field(
        default="https://lemmasub.net/miners/",
        validation_alias="LEMMA_PUBLIC_DASHBOARD_URL",
    )
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    synapse_max_statement_chars: int = Field(default=500_000, ge=1, validation_alias="SYNAPSE_MAX_STATEMENT_CHARS")
    synapse_max_proof_chars: int = Field(default=500_000, ge=1, validation_alias="SYNAPSE_MAX_PROOF_CHARS")

    def validator_wallet_names(self) -> tuple[str, str]:
        cold = (self.validator_wallet_cold or "").strip() or self.wallet_cold
        hot = (self.validator_wallet_hot or "").strip() or self.wallet_hot
        return cold, hot
