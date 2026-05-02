"""Environment-driven settings."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LemmaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    netuid: int = Field(default=0, ge=0, validation_alias=AliasChoices("NETUID", "netuid"))

    problem_source: Literal["generated", "frozen"] = Field(
        default="generated",
        validation_alias=AliasChoices("LEMMA_PROBLEM_SOURCE", "problem_source"),
        description="generated = seed-expanded templates; frozen = minif2f_frozen.json catalog.",
    )
    problem_seed_quantize_blocks: int = Field(
        default=25,
        ge=1,
        le=1_000_000,
        validation_alias=AliasChoices(
            "LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS",
            "problem_seed_quantize_blocks",
        ),
        description=(
            "Validators use problem_seed = (chain_head // N) * N. Default 25 ≈ 5 min of "
            "Finney blocks (~12 s each), keeping peers on the same theorem within that window."
        ),
    )
    minif2f_catalog_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("LEMMA_MINIF2F_CATALOG_PATH", "minif2f_catalog_path"),
        description="Optional path to frozen JSON array (default: bundled lemma/problems/minif2f_frozen.json).",
    )
    generated_registry_expected_sha256: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED",
            "generated_registry_expected_sha256",
        ),
        description="If set, validator exits in generated mode unless registry matches.",
    )
    subtensor_network: str = Field(
        default="finney",
        validation_alias=AliasChoices("SUBTENSOR_NETWORK", "subtensor_network"),
    )
    subtensor_chain_endpoint: str | None = Field(
        default=None,
        validation_alias=AliasChoices("SUBTENSOR_CHAIN_ENDPOINT", "subtensor_chain_endpoint"),
    )

    wallet_cold: str = Field(
        default="default",
        validation_alias=AliasChoices("BT_WALLET_COLD", "wallet_cold"),
    )
    wallet_hot: str = Field(
        default="default",
        validation_alias=AliasChoices("BT_WALLET_HOT", "wallet_hot"),
    )

    axon_port: int = Field(default=8091, validation_alias=AliasChoices("AXON_PORT", "axon_port"))
    axon_external_ip: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AXON_EXTERNAL_IP", "axon_external_ip"),
        description="Public IPv4/host validators use to reach this axon; leave unset to auto-discover.",
    )
    axon_discover_external_ip: bool = Field(
        default=True,
        validation_alias=AliasChoices("AXON_DISCOVER_EXTERNAL_IP", "axon_discover_external_ip"),
        description="If AXON_EXTERNAL_IP is unset, fetch public IPv4 over HTTPS before serving.",
    )

    lean_sandbox_image: str = Field(
        default="lemma/lean-sandbox:latest",
        validation_alias=AliasChoices("LEAN_SANDBOX_IMAGE", "lean_sandbox_image"),
    )
    lean_verify_timeout_s: int = Field(
        default=300,
        ge=1,
        validation_alias=AliasChoices("LEAN_VERIFY_TIMEOUT_S", "lean_verify_timeout_s"),
        description=(
            "Seconds for Docker/host lake build + axiom check per miner submission. "
            "Default 300 (5m); raise for heavy Mathlib builds if timeouts are false positives."
        ),
    )
    lean_sandbox_cpu: float = Field(
        default=2.0,
        validation_alias=AliasChoices("LEAN_SANDBOX_CPU", "lean_sandbox_cpu"),
    )
    lean_sandbox_mem_mb: int = Field(
        default=8192,
        validation_alias=AliasChoices("LEAN_SANDBOX_MEM_MB", "lean_sandbox_mem_mb"),
    )
    lean_sandbox_network: str = Field(
        default="none",
        validation_alias=AliasChoices("LEAN_SANDBOX_NETWORK", "lean_sandbox_network"),
    )

    judge_provider: str = Field(
        default="openai",
        validation_alias=AliasChoices("JUDGE_PROVIDER", "judge_provider"),
        description="Subnet default: OpenAI-compatible API (Chutes Qwen3-32B-TEE; override for vLLM/OpenAI).",
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "anthropic_api_key"),
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        validation_alias=AliasChoices("ANTHROPIC_MODEL", "anthropic_model"),
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "openai_api_key"),
    )
    openai_model: str = Field(
        default="Qwen/Qwen3-32B-TEE",
        validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"),
        description="Judge model id (Chutes default; use your vLLM/HF id when self-hosting).",
    )
    openai_base_url: str = Field(
        default="https://llm.chutes.ai/v1",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "openai_base_url"),
        description="OpenAI-compatible API base (Chutes llm endpoint by default; use localhost for vLLM).",
    )
    judge_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        validation_alias=AliasChoices("JUDGE_TEMPERATURE", "judge_temperature"),
        description="Sampling temperature for Anthropic and OpenAI judges (symmetric defaults).",
    )
    judge_max_tokens: int = Field(
        default=256,
        ge=16,
        le=4096,
        validation_alias=AliasChoices("JUDGE_MAX_TOKENS", "judge_max_tokens"),
        description="Max completion tokens for judge responses (short JSON rubric).",
    )
    judge_profile_expected_sha256: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "JUDGE_PROFILE_SHA256_EXPECTED",
            "judge_profile_expected_sha256",
        ),
        description="If set, validator refuses to run unless judge_profile_sha256 matches.",
    )

    prover_provider: str = Field(
        default="anthropic",
        validation_alias=AliasChoices("PROVER_PROVIDER", "prover_provider"),
    )
    prover_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROVER_MODEL", "prover_model"),
    )

    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "log_level"))

    # Validator — dendrite query / chain writes
    dendrite_timeout_s: float = Field(
        default=300.0,
        gt=0,
        validation_alias=AliasChoices("DENDRITE_TIMEOUT_S", "dendrite_timeout_s"),
        description=(
            "Seconds for miner HTTP response per challenge (synapse deadline). "
            "Default 300 (5m); subnet operators should match across validators."
        ),
    )
    validator_round_interval_s: float = Field(
        default=300.0,
        gt=0,
        validation_alias=AliasChoices(
            "LEMMA_VALIDATOR_ROUND_INTERVAL_S",
            "validator_round_interval_s",
        ),
        description=(
            "Seconds between validator rounds when not aligning to chain epochs. "
            "Default 300 (5m)."
        ),
    )
    validator_align_rounds_to_epoch: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH",
            "validator_align_rounds_to_epoch",
        ),
        description=(
            "If true, wait for subnet epoch boundaries before each round (legacy). "
            "If false (default), sleep validator_round_interval_s between rounds."
        ),
    )
    set_weights_max_retries: int = Field(
        default=3,
        ge=1,
        le=20,
        validation_alias=AliasChoices("SET_WEIGHTS_MAX_RETRIES", "set_weights_max_retries"),
    )
    set_weights_retry_delay_s: float = Field(
        default=2.0,
        ge=0.1,
        validation_alias=AliasChoices("SET_WEIGHTS_RETRY_DELAY_S", "set_weights_retry_delay_s"),
    )
    empty_epoch_weights_policy: Literal["skip", "uniform"] = Field(
        default="skip",
        validation_alias=AliasChoices("EMPTY_EPOCH_WEIGHTS_POLICY", "empty_epoch_weights_policy"),
        description="If no miner passes verify+judge: skip set_weights, or emit uniform weights across all UIDs.",
    )
    validator_abort_if_not_registered: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "VALIDATOR_ABORT_IF_NOT_REGISTERED",
            "validator_abort_if_not_registered",
        ),
        description="If true, skip epochs when this wallet has no UID on the subnet.",
    )
    training_export_jsonl: Path | None = Field(
        default=None,
        validation_alias=AliasChoices("LEMMA_TRAINING_EXPORT_JSONL", "training_export_jsonl"),
        description="Append one JSON object per scored miner per epoch (PRM dataset export).",
    )

    # Miner — resource limits and validator gate
    miner_min_validator_stake: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias=AliasChoices("MINER_MIN_VALIDATOR_STAKE", "miner_min_validator_stake"),
        description="Minimum metagraph stake (TAO) for caller hotkey; 0 disables check.",
    )
    miner_metagraph_refresh_s: float = Field(
        default=300.0,
        ge=5.0,
        validation_alias=AliasChoices("MINER_METAGRAPH_REFRESH_S", "miner_metagraph_refresh_s"),
    )
    miner_max_concurrent_forwards: int = Field(
        default=8,
        ge=1,
        le=256,
        validation_alias=AliasChoices("MINER_MAX_CONCURRENT_FORWARDS", "miner_max_concurrent_forwards"),
    )
    miner_max_forwards_per_day: int = Field(
        default=0,
        ge=0,
        validation_alias=AliasChoices("MINER_MAX_FORWARDS_PER_DAY", "miner_max_forwards_per_day"),
        description="If >0, refuse new forwards after this many successful invokes per UTC day (0=unlimited).",
    )
    miner_require_validator_permit: bool = Field(
        default=False,
        validation_alias=AliasChoices("MINER_REQUIRE_VALIDATOR_PERMIT", "miner_require_validator_permit"),
    )
    miner_priority_by_stake: bool = Field(
        default=False,
        validation_alias=AliasChoices("MINER_PRIORITY_BY_STAKE", "miner_priority_by_stake"),
        description="Use validator stake as axon priority (requires periodic metagraph sync).",
    )
    synapse_max_statement_chars: int = Field(
        default=500_000,
        ge=1024,
        validation_alias=AliasChoices("SYNAPSE_MAX_STATEMENT_CHARS", "synapse_max_statement_chars"),
    )
    synapse_max_proof_chars: int = Field(
        default=500_000,
        ge=1024,
        validation_alias=AliasChoices("SYNAPSE_MAX_PROOF_CHARS", "synapse_max_proof_chars"),
    )
    synapse_max_trace_chars: int = Field(
        default=400_000,
        ge=1024,
        validation_alias=AliasChoices("SYNAPSE_MAX_TRACE_CHARS", "synapse_max_trace_chars"),
    )
