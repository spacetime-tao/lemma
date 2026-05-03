"""Environment-driven settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

# Subnet policy: OpenAI-compatible judge model id (Chutes HF-style). Validators must match unless opted out.
CANONICAL_JUDGE_OPENAI_MODEL = "deepseek-ai/DeepSeek-V3.2-TEE"


class LemmaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Prefer ``.env`` over process environment for the same variable name.

        Default pydantic-settings order lets exported shell variables beat ``merge_dotenv`` / ``lemma setup``.
        Explicit constructor kwargs still win (handled first). Set ``LEMMA_PREFER_PROCESS_ENV=1`` to restore
        the library default (environment overrides ``.env``) for CI/containers that rely on it.
        """
        if os.environ.get("LEMMA_PREFER_PROCESS_ENV", "").strip().lower() in (
            "1",
            "true",
            "yes",
        ):
            return (
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            )
        return (
            init_settings,
            dotenv_settings,
            env_settings,
            file_secret_settings,
        )

    netuid: int = Field(default=0, ge=0, validation_alias=AliasChoices("NETUID", "netuid"))

    problem_source: Literal["generated", "frozen"] = Field(
        default="generated",
        validation_alias=AliasChoices("LEMMA_PROBLEM_SOURCE", "problem_source"),
        description="generated = seed-expanded templates; frozen = minif2f_frozen.json catalog.",
    )
    problem_seed_quantize_blocks: int = Field(
        default=100,
        ge=1,
        le=1_000_000,
        validation_alias=AliasChoices(
            "LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS",
            "problem_seed_quantize_blocks",
        ),
        description=(
            "Used when LEMMA_PROBLEM_SEED_MODE=quantize: problem_seed = (chain_head // N) * N "
            "(e.g. N=100 and ~12 s/block ≈ 20 min per theorem). "
            "Also subnet_epoch fallback if Tempo query fails."
        ),
    )
    problem_seed_mode: Literal["quantize", "subnet_epoch"] = Field(
        default="quantize",
        validation_alias=AliasChoices("LEMMA_PROBLEM_SEED_MODE", "problem_seed_mode"),
        description=(
            "quantize: fixed N-block windows (`LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`) — same theorem for everyone "
            "between rotations. "
            "subnet_epoch: seed from subnet Tempo stride via chain RPC (alternative cadence)."
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
    validator_wallet_cold: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "BT_VALIDATOR_WALLET_COLD",
            "LEMMA_VALIDATOR_WALLET_COLD",
            "validator_wallet_cold",
        ),
        description="If set, `lemma validator` / `validator-check` use this coldkey instead of BT_WALLET_COLD.",
    )
    validator_wallet_hot: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "BT_VALIDATOR_WALLET_HOT",
            "LEMMA_VALIDATOR_WALLET_HOT",
            "validator_wallet_hot",
        ),
        description="If set, validator uses this hotkey name instead of BT_WALLET_HOT.",
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
        description=(
            "Subnet default: OpenAI-compatible API on Chutes. Validators must use OPENAI_MODEL="
            f"{CANONICAL_JUDGE_OPENAI_MODEL!r} unless LEMMA_ALLOW_NONCANONICAL_JUDGE_MODEL=1."
        ),
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
        default=CANONICAL_JUDGE_OPENAI_MODEL,
        validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"),
        description=(
            f"Judge model id when JUDGE_PROVIDER=openai (default {CANONICAL_JUDGE_OPENAI_MODEL!r} on Chutes). "
            "Self-hosted vLLM: use the same HF-style id as loaded weights."
        ),
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
    allow_noncanonical_judge_model: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_ALLOW_NONCANONICAL_JUDGE_MODEL",
            "allow_noncanonical_judge_model",
        ),
        description=(
            "If false (default), validators with JUDGE_PROVIDER=openai must set OPENAI_MODEL to "
            f"{CANONICAL_JUDGE_OPENAI_MODEL!r}. Set true only for local experiments."
        ),
    )

    prover_provider: str = Field(
        default="anthropic",
        validation_alias=AliasChoices("PROVER_PROVIDER", "prover_provider"),
    )
    prover_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROVER_MODEL", "prover_model"),
        description="Miner-only model id. Use a capable reasoning model; see docs/MODELS.md.",
    )
    prover_max_tokens: int = Field(
        default=32_768,
        ge=512,
        le=131_072,
        validation_alias=AliasChoices(
            "LEMMA_PROVER_MAX_TOKENS",
            "PROVER_MAX_TOKENS",
            "prover_max_tokens",
        ),
        description=(
            "Max completion tokens for one prover call (reasoning JSON + Submission.lean). "
            "OpenAI-compatible: sent as max_tokens. Anthropic: capped at 8192 (API limit for many models)."
        ),
    )
    prover_llm_retry_attempts: int = Field(
        default=4,
        ge=1,
        le=32,
        validation_alias=AliasChoices(
            "LEMMA_PROVER_LLM_RETRY_ATTEMPTS",
            "PROVER_LLM_RETRY_ATTEMPTS",
            "prover_llm_retry_attempts",
        ),
        description=(
            "How many times to call the prover LLM on transient errors (429, timeouts, 5xx) per forward. "
            "Backoff between tries grows (capped); raising this helps saturated gateways but uses more wall time."
        ),
    )
    prover_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        validation_alias=AliasChoices(
            "LEMMA_PROVER_TEMPERATURE",
            "PROVER_TEMPERATURE",
            "prover_temperature",
        ),
        description="Sampling temperature for prover completions (OpenAI-compatible and Anthropic prover paths).",
    )
    prover_system_append: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LEMMA_PROVER_SYSTEM_APPEND",
            "prover_system_append",
        ),
        description=(
            "Appended to the built-in prover system prompt on every LLM call (after PROVER_SYSTEM). "
            "Use for operator tone/style (e.g. lay audience). Does not replace JSON/proof rules."
        ),
    )
    prover_min_reasoning_steps: int = Field(
        default=0,
        ge=0,
        le=64,
        validation_alias=AliasChoices(
            "LEMMA_PROVER_MIN_REASONING_STEPS",
            "prover_min_reasoning_steps",
        ),
        description=(
            "If > 0, reject prover JSON unless reasoning_steps has at least this many steps after parsing. "
            "0 = no minimum (subnet default)."
        ),
    )
    prover_min_reasoning_total_chars: int = Field(
        default=0,
        ge=0,
        le=500_000,
        validation_alias=AliasChoices(
            "LEMMA_PROVER_MIN_REASONING_TOTAL_CHARS",
            "prover_min_reasoning_total_chars",
        ),
        description=(
            "If > 0, reject unless the sum of trimmed reasoning step text lengths meets this minimum. 0 = off."
        ),
    )
    prover_min_proof_script_chars: int = Field(
        default=0,
        ge=0,
        le=500_000,
        validation_alias=AliasChoices(
            "LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS",
            "prover_min_proof_script_chars",
        ),
        description=(
            "If > 0, reject JSON unless proof_script (full Submission.lean string) has at least this many "
            "characters after strip. 0 = off (default). Use to force longer formal proofs on your miner."
        ),
    )

    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "log_level"))

    # Validator — forward query (HTTP wait derived from block height × block time)
    llm_http_timeout_s: float = Field(
        default=900.0,
        gt=30.0,
        validation_alias=AliasChoices("LEMMA_LLM_HTTP_TIMEOUT_S", "llm_http_timeout_s"),
        description=(
            "HTTP read timeout for OpenAI-compatible + Anthropic LLM calls (prover + judge). "
            "Should fit inside one round’s forward wait (blocks × LEMMA_BLOCK_TIME_SEC_ESTIMATE)."
        ),
    )
    block_time_sec_estimate: float = Field(
        default=12.0,
        gt=0,
        le=60.0,
        validation_alias=AliasChoices("LEMMA_BLOCK_TIME_SEC_ESTIMATE", "block_time_sec_estimate"),
        description="Rough seconds per chain block — converts remaining blocks to forward HTTP timeout.",
    )
    forward_wait_min_s: float = Field(
        default=60.0,
        gt=0,
        validation_alias=AliasChoices("LEMMA_FORWARD_WAIT_MIN_S", "forward_wait_min_s"),
        description="Floor for forward HTTP timeout after blocks×block-time (avoid unusably short waits).",
    )
    forward_wait_max_s: float = Field(
        default=86400.0,
        gt=0,
        validation_alias=AliasChoices("LEMMA_FORWARD_WAIT_MAX_S", "forward_wait_max_s"),
        description="Ceiling for forward HTTP timeout (safety cap even when many blocks remain).",
    )
    miner_reject_past_deadline_block: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LEMMA_MINER_REJECT_PAST_DEADLINE_BLOCK",
            "miner_reject_past_deadline_block",
        ),
        description="If true, refuse axon work when chain head >= synapse.deadline_block (when set).",
    )
    validator_enforce_published_meta: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META",
            "validator_enforce_published_meta",
        ),
        description=(
            "If true, refuse to start validator unless JUDGE_PROFILE_SHA256_EXPECTED is set and "
            "(for generated problems) LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED is set — "
            "subnet policy pins from `lemma meta --raw`."
        ),
    )
    timeout_scale_by_split: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_TIMEOUT_SCALE_BY_SPLIT",
            "timeout_scale_by_split",
        ),
        description=(
            "If true, multiply forward HTTP wait and LEAN_VERIFY_TIMEOUT_S by easy/medium/hard multipliers."
        ),
    )
    timeout_split_easy_mult: float = Field(
        default=1.0,
        ge=0.1,
        le=50.0,
        validation_alias=AliasChoices(
            "LEMMA_TIMEOUT_SPLIT_EASY_MULT",
            "timeout_split_easy_mult",
        ),
    )
    timeout_split_medium_mult: float = Field(
        default=1.5,
        ge=0.1,
        le=50.0,
        validation_alias=AliasChoices(
            "LEMMA_TIMEOUT_SPLIT_MEDIUM_MULT",
            "timeout_split_medium_mult",
        ),
    )
    timeout_split_hard_mult: float = Field(
        default=2.0,
        ge=0.1,
        le=50.0,
        validation_alias=AliasChoices(
            "LEMMA_TIMEOUT_SPLIT_HARD_MULT",
            "timeout_split_hard_mult",
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
    miner_log_forwards: bool = Field(
        default=False,
        validation_alias=AliasChoices("LEMMA_MINER_LOG_FORWARDS", "miner_log_forwards"),
        description="Log reasoning trace and proof_script for each forward (excerpts at INFO).",
    )
    miner_forward_summary: bool = Field(
        default=True,
        validation_alias=AliasChoices("LEMMA_MINER_FORWARD_SUMMARY", "miner_forward_summary"),
        description=(
            "One INFO line per forward: theorem id, split, sizes, timing; optional session totals. "
            "Disable for quieter logs."
        ),
    )
    miner_local_verify: bool = Field(
        default=False,
        validation_alias=AliasChoices("LEMMA_MINER_LOCAL_VERIFY", "miner_local_verify"),
        description="Run Lean sandbox on Submission.lean after prover returns (same Docker/host as validators).",
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

    def validator_wallet_names(self) -> tuple[str, str]:
        """Cold/hot key names for signing and metagraph (validator). Falls back to BT_WALLET_*."""
        c = (self.validator_wallet_cold or "").strip()
        h = (self.validator_wallet_hot or "").strip()
        return (c or self.wallet_cold, h or self.wallet_hot)


def canonical_openai_judge_model_issue(settings: LemmaSettings) -> str | None:
    """Return a human-readable problem description, or None if OpenAI judge model policy is satisfied."""
    if os.environ.get("LEMMA_FAKE_JUDGE") == "1":
        return None
    if (settings.judge_provider or "").lower() != "openai":
        return None
    if settings.allow_noncanonical_judge_model:
        return None
    got = (settings.openai_model or "").strip()
    if got != CANONICAL_JUDGE_OPENAI_MODEL:
        return (
            f"OPENAI_MODEL must be {CANONICAL_JUDGE_OPENAI_MODEL!r} for subnet validators "
            f"(got {got!r}). Set LEMMA_ALLOW_NONCANONICAL_JUDGE_MODEL=1 only for experiments."
        )
    return None


def assert_canonical_openai_judge_model(settings: LemmaSettings) -> None:
    """Raise ``SystemExit`` if validator judge stack violates subnet OpenAI model policy."""
    msg = canonical_openai_judge_model_issue(settings)
    if msg:
        raise SystemExit(msg)
