"""Environment-driven settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

# Subnet judge (validators only): DeepSeek on Chutes — see ``validator_judge_stack_strict_issue``.
CANONICAL_JUDGE_OPENAI_MODEL = "deepseek-ai/DeepSeek-V3.2-TEE"
CANONICAL_JUDGE_OPENAI_BASE_URL = "https://llm.chutes.ai/v1"


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

        Default pydantic-settings order lets exported shell variables beat ``merge_dotenv`` / ``lemma-cli setup``.
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
    lemma_dev_allow_frozen_problem_source: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE",
            "lemma_dev_allow_frozen_problem_source",
        ),
        description=(
            "Allow LEMMA_PROBLEM_SOURCE=frozen (bundled public-eval catalog). Default false — "
            "subnet-like deployments should use generated templates."
        ),
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
    lemma_problem_seed_chain_head_slack_blocks: int = Field(
        default=0,
        ge=0,
        le=128,
        validation_alias=AliasChoices(
            "LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS",
            "lemma_problem_seed_chain_head_slack_blocks",
        ),
        description=(
            "Subtract this many blocks from RPC chain head before problem_seed resolution and forward HTTP "
            "deadline math (same value used for both). Default 0; try 1 if validators disagree on theorem by "
            "one block near quantize boundaries."
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
        description=(
            "Validators with LEMMA_PROBLEM_SOURCE=generated must set this; startup fails unless it matches "
            "the live generated-registry hash (`lemma meta`)."
        ),
    )
    lemma_generated_legacy_plain_rng: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_GENERATED_LEGACY_PLAIN_RNG",
            "lemma_generated_legacy_plain_rng",
        ),
        description=(
            "If true, template RNG uses random.Random(chain_seed) (legacy). Default false: SHA256-mix chain seed "
            "before RNG for less correlated template picks across adjacent seeds (see lemma/problems/generated.py)."
        ),
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
    lean_use_docker: bool = Field(
        default=True,
        validation_alias=AliasChoices("LEMMA_USE_DOCKER", "lean_use_docker"),
        description=(
            "When true (default), validators/miners/`lemma verify` use Docker for LeanSandbox — subnet parity. "
            "Set false only for host `lake` when toolchain matches `LEAN_SANDBOX_IMAGE` and policy allows."
        ),
    )
    allow_host_lean: bool = Field(
        default=False,
        validation_alias=AliasChoices("LEMMA_ALLOW_HOST_LEAN", "allow_host_lean"),
        description=(
            "If true, allow `lemma verify --host-lean`, `lemma-cli try-prover --host-lean`, and "
            "`LEMMA_TRY_PROVER_HOST_VERIFY` for local debugging. Production validators should leave this false."
        ),
    )

    judge_provider: str = Field(
        default="chutes",
        validation_alias=AliasChoices("JUDGE_PROVIDER", "judge_provider"),
        description=(
            "``chutes`` = subnet judge via OpenAI-compatible HTTP to Chutes "
            "(same stack as ``lemma-cli configure judge`` "
            f"→ Chutes). Legacy alias: ``openai``. Anthropic: ``anthropic``. Validators must use ``chutes`` with "
            f"OPENAI_MODEL={CANONICAL_JUDGE_OPENAI_MODEL!r} and OPENAI_BASE_URL={CANONICAL_JUDGE_OPENAI_BASE_URL!r}."
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
        description=(
            "Legacy fallback: Chutes/OpenAI-compatible API key for the **judge** when JUDGE_OPENAI_API_KEY is unset. "
            "Prefer JUDGE_OPENAI_API_KEY so Gemini/prover keys can live under PROVER_OPENAI_API_KEY only."
        ),
    )
    judge_openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("JUDGE_OPENAI_API_KEY", "judge_openai_api_key"),
        description=(
            "Chutes/OpenAI-compatible API key used **only** by the judge (scores traces). "
            "If unset, the judge falls back to OPENAI_API_KEY."
        ),
    )
    openai_model: str = Field(
        default=CANONICAL_JUDGE_OPENAI_MODEL,
        validation_alias=AliasChoices("OPENAI_MODEL", "openai_model"),
        description=(
            f"Judge model when JUDGE_PROVIDER is chutes or openai. Validators must use "
            f"{CANONICAL_JUDGE_OPENAI_MODEL!r} (miners: use PROVER_MODEL for a different prover id)."
        ),
    )
    openai_base_url: str = Field(
        default="https://llm.chutes.ai/v1",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "openai_base_url"),
        description=(
            f"Judge API base. Validators must use {CANONICAL_JUDGE_OPENAI_BASE_URL!r}; miners may point "
            "`PROVER_OPENAI_BASE_URL` elsewhere."
        ),
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
    judge_llm_retry_attempts: int = Field(
        default=4,
        ge=1,
        le=32,
        validation_alias=AliasChoices(
            "LEMMA_JUDGE_LLM_RETRY_ATTEMPTS",
            "judge_llm_retry_attempts",
        ),
        description="Judge-only retries on 429 / timeouts / 5xx for each score() call.",
    )
    judge_llm_http_timeout_s: float | None = Field(
        default=None,
        gt=0.0,
        validation_alias=AliasChoices(
            "LEMMA_JUDGE_HTTP_TIMEOUT_S",
            "judge_llm_http_timeout_s",
        ),
        description=(
            "If set, overrides LEMMA_LLM_HTTP_TIMEOUT_S for judge HTTP reads only "
            "(small JSON output; use a tighter cap to fail fast on stalls)."
        ),
    )
    judge_profile_expected_sha256: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "JUDGE_PROFILE_SHA256_EXPECTED",
            "judge_profile_expected_sha256",
        ),
        description=(
            "Validators must set this; startup fails unless it matches live judge_profile_sha256 "
            "(`lemma meta`)."
        ),
    )
    allow_noncanonical_judge_model: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_ALLOW_NONCANONICAL_JUDGE_MODEL",
            "allow_noncanonical_judge_model",
        ),
        description=(
            "Ignored by ``lemma validator`` (validators always use the Chutes DeepSeek judge). "
            "Reserved for future non-validator tooling."
        ),
    )

    prover_provider: str = Field(
        default="anthropic",
        validation_alias=AliasChoices("PROVER_PROVIDER", "prover_provider"),
    )
    prover_model: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROVER_MODEL", "prover_model"),
        description="Miner-only model id. Use a capable reasoning model; see docs/models.md.",
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
    prover_openai_base_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROVER_OPENAI_BASE_URL", "prover_openai_base_url"),
        description=(
            "Miner-only: OpenAI-compatible API base for PROVER_PROVIDER=openai. "
            "If unset, prover uses OPENAI_BASE_URL (validator judge is unchanged)."
        ),
    )
    prover_openai_api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("PROVER_OPENAI_API_KEY", "prover_openai_api_key"),
        description=(
            "Miner-only: API key for the prover’s OpenAI-compatible endpoint. "
            "If unset, prover falls back to OPENAI_API_KEY."
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
    lemma_lean_verify_max_concurrent: int = Field(
        default=4,
        ge=1,
        le=128,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_VERIFY_MAX_CONCURRENT",
            "lemma_lean_verify_max_concurrent",
        ),
        description=(
            "Max concurrent Lean sandbox.verify jobs per epoch (each may spawn Docker). "
            "Raise on large validators when many miners return proofs; lower if CPU/RAM or Docker struggles."
        ),
    )
    lemma_judge_max_concurrent: int = Field(
        default=8,
        ge=1,
        le=256,
        validation_alias=AliasChoices(
            "LEMMA_JUDGE_MAX_CONCURRENT",
            "lemma_judge_max_concurrent",
        ),
        description=(
            "Max concurrent judge LLM HTTP calls per epoch (after Lean passes). "
            "Caps bursts against Chutes/Anthropic to reduce 429 rate limits when many miners verify."
        ),
    )
    lean_verify_workspace_cache_dir: Path | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR",
            "lean_verify_workspace_cache_dir",
        ),
        description=(
            "Optional directory on fast local disk to reuse a warm `.lake` per theorem template. "
            "After the first passing verify for a template, later verifies only rebuild ``Submission`` "
            "(same subnet epoch = same template for all miners). Creates subdirs; prune manually if huge."
        ),
    )
    lemma_lean_workspace_cache_include_submission_hash: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH",
            "lemma_lean_workspace_cache_include_submission_hash",
        ),
        description=(
            "If true, cache slot names include a truncated SHA256 of Submission.lean (distinct proofs never "
            "share a directory; more disk vs template-only keys). Default false."
        ),
    )
    lemma_lean_proof_metrics_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_PROOF_METRICS",
            "lemma_lean_proof_metrics_enabled",
        ),
        description=(
            "Opt-in compare-only Lean proof metrics in VerifyResult. Does not affect rewards or weights."
        ),
    )
    lemma_lean_docker_worker: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_DOCKER_WORKER",
            "lemma_lean_docker_worker",
        ),
        description=(
            "Name of a **running** sandbox container: Lemma uses `docker exec` instead of `docker run` per "
            "verify (much lower latency). Must bind-mount `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` — see "
            "docs/validator.md and scripts/start_lean_docker_worker.sh."
        ),
    )
    lean_verify_remote_url: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_VERIFY_REMOTE_URL",
            "lean_verify_remote_url",
        ),
        description=(
            "Optional base URL (http/https) of a dedicated Lean verify worker process "
            "(POST `/verify` JSON — see `lemma lean-worker`). When unset, verification runs in-process "
            "via `LeanSandbox` on this machine."
        ),
    )
    lean_verify_remote_bearer: str | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_VERIFY_REMOTE_BEARER",
            "lean_verify_remote_bearer",
        ),
        description=(
            "Optional shared secret; sent as ``Authorization: Bearer`` when calling "
            "``LEMMA_LEAN_VERIFY_REMOTE_URL``."
        ),
    )
    lean_verify_remote_timeout_margin_s: float = Field(
        default=30.0,
        ge=0.0,
        le=600.0,
        validation_alias=AliasChoices(
            "LEMMA_LEAN_VERIFY_REMOTE_TIMEOUT_MARGIN_S",
            "lean_verify_remote_timeout_margin_s",
        ),
        description=(
            "Added to ``LEAN_VERIFY_TIMEOUT_S`` (per-request split scaling included) "
            "for HTTP client read timeout."
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
    lemma_training_export_profile: Literal["full", "reasoning_only"] = Field(
        default="full",
        validation_alias=AliasChoices(
            "LEMMA_TRAINING_EXPORT_PROFILE",
            "lemma_training_export_profile",
        ),
        description=(
            "`full`: schema v1 includes proof_script, rubric, pareto_weight. "
            "`reasoning_only`: schema v2 omits proof, judge labels, and weights — less useful for gaming "
            "(see docs/training_export.md)."
        ),
    )

    # Scoring / incentive hard-migration (validators)
    lemma_score_proof_weight: float = Field(
        default=0.10,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("LEMMA_SCORE_PROOF_WEIGHT", "lemma_score_proof_weight"),
        description=(
            "Blend intrinsic proof-text heuristic with judge rubric: "
            "round_score = w * proof_intrinsic + (1-w) * judge_composite. "
            "Default keeps the text heuristic low-weight (see docs/proof-intrinsic-decision.md)."
        ),
    )
    lemma_scoring_dedup_identical: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LEMMA_SCORING_DEDUP_IDENTICAL",
            "lemma_scoring_dedup_identical",
        ),
        description="Collapse identical (theorem, proof, trace) submissions; keep best round score per cluster.",
    )
    lemma_scoring_coldkey_dedup: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LEMMA_SCORING_COLDKEY_DEDUP",
            "lemma_scoring_coldkey_dedup",
        ),
        description="Keep only the best-scoring hotkey per coldkey (metagraph.coldkeys) each epoch.",
    )
    lemma_reputation_ema_alpha: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "LEMMA_REPUTATION_EMA_ALPHA",
            "lemma_reputation_ema_alpha",
        ),
        description="EMA smoothing for per-UID scores before Pareto weights (0 disables smoothing).",
    )
    lemma_reputation_credibility_exponent: float = Field(
        default=1.0,
        ge=0.0,
        le=4.0,
        validation_alias=AliasChoices(
            "LEMMA_REPUTATION_CREDIBILITY_EXPONENT",
            "lemma_reputation_credibility_exponent",
        ),
        description=(
            "Multiply EMA-smoothed score by (verify credibility)**exponent. "
            "Exponent 0 disables the multiplier (always 1). Default 1 applies a linear credibility curve."
        ),
    )
    lemma_reputation_verify_credibility_alpha: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA",
            "lemma_reputation_verify_credibility_alpha",
        ),
        description=(
            "EMA alpha for per-UID verify credibility (1.0 = Lean verify passed, 0.0 = failed). "
            "0 disables updates; new UIDs start at credibility 1.0."
        ),
    )
    lemma_proof_intrinsic_strip_comments: bool = Field(
        default=True,
        validation_alias=AliasChoices(
            "LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS",
            "lemma_proof_intrinsic_strip_comments",
        ),
        description="Strip Lean line/block comments before proof_intrinsic heuristic (reduces comment-padding).",
    )
    lemma_reputation_state_path: Path | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "LEMMA_REPUTATION_STATE_PATH",
            "lemma_reputation_state_path",
        ),
        description="JSON file for per-UID EMA persistence (default: ~/.lemma/validator_reputation.json).",
    )
    lemma_epoch_problem_count: int = Field(
        default=1,
        ge=1,
        le=32,
        validation_alias=AliasChoices(
            "LEMMA_EPOCH_PROBLEM_COUNT",
            "lemma_epoch_problem_count",
        ),
        description="Number of distinct theorems sampled per validator epoch (sequential miner queries).",
    )
    lemma_commit_reveal_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_COMMIT_REVEAL_ENABLED",
            "lemma_commit_reveal_enabled",
        ),
        description=(
            "Two-phase challenge: validator queries commit (hash) then reveal (proof + nonce). "
            "See docs/commit-reveal.md and lemma/protocol_commit_reveal.py."
        ),
    )
    lemma_miner_verify_attest_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_MINER_VERIFY_ATTEST_ENABLED",
            "lemma_miner_verify_attest_enabled",
        ),
        description=(
            "Validators require Sr25519 attest signatures on miner responses; miners must run "
            "`LEMMA_MINER_LOCAL_VERIFY=1` and sign after local PASS. See docs/miner-verify-attest.md."
        ),
    )
    lemma_miner_verify_attest_spot_verify_fraction: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices(
            "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION",
            "lemma_miner_verify_attest_spot_verify_fraction",
        ),
        description=(
            "Deterministic fraction of miner responses that still run full validator Lean verify "
            "(rest trusted via attest only). 1.0 = always verify (default); 0.15 ≈ 15% heavy verify."
        ),
    )
    lemma_miner_verify_attest_spot_verify_salt: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT",
            "lemma_miner_verify_attest_spot_verify_salt",
        ),
        description=(
            "Optional validator/operator salt mixed into attest spot-verify selection. Keep non-empty salts "
            "out of public docs; lemma meta exposes only a SHA256 fingerprint."
        ),
    )
    lemma_judge_profile_attest_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_JUDGE_PROFILE_ATTEST_ENABLED",
            "lemma_judge_profile_attest_enabled",
        ),
        description=(
            "Optional HTTP peer quorum: each URL must return this validator's judge_profile_sha256. "
            "See LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS, LEMMA_JUDGE_PROFILE_ATTEST_SKIP, "
            "`lemma validator judge-attest-serve`, docs/incentive_migration.md."
        ),
    )
    lemma_judge_profile_attest_peer_urls: str = Field(
        default="",
        validation_alias=AliasChoices(
            "LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS",
            "lemma_judge_profile_attest_peer_urls",
        ),
        description=(
            "Comma-separated GET URLs probed when LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1 (plaintext hex or JSON "
            "with judge_profile_sha256)."
        ),
    )
    lemma_judge_profile_attest_allow_skip: bool = Field(
        default=False,
        validation_alias=AliasChoices(
            "LEMMA_JUDGE_PROFILE_ATTEST_SKIP",
            "lemma_judge_profile_attest_allow_skip",
        ),
        description=(
            "When attest is enabled, skip peer HTTP (solo / dev). Logs as WARN at validator startup — "
            "not for production multi-validator alignment."
        ),
    )
    lemma_judge_profile_attest_http_timeout_s: float = Field(
        default=15.0,
        ge=1.0,
        le=300.0,
        validation_alias=AliasChoices(
            "LEMMA_JUDGE_PROFILE_ATTEST_HTTP_TIMEOUT_S",
            "lemma_judge_profile_attest_http_timeout_s",
        ),
        description="Per-URL HTTP timeout when LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1.",
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
    miner_forward_timeline: bool = Field(
        default=False,
        validation_alias=AliasChoices("LEMMA_MINER_FORWARD_TIMELINE", "miner_forward_timeline"),
        description=(
            "Per forward, log three INFO lines: (1) RECEIVE with deadline vs chain head, (2) SOLVED after prover, "
            "(3) OUTCOME with local_lean or hint to enable LEMMA_MINER_LOCAL_VERIFY. "
            "Final validator Lean+judge is not returned on the axon."
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

    def prover_openai_base_url_resolved(self) -> str:
        """OpenAI-compatible base URL for the miner prover; defaults to judge ``OPENAI_BASE_URL``."""
        p = (self.prover_openai_base_url or "").strip()
        return p if p else (self.openai_base_url or "").strip()

    def prover_openai_api_key_resolved(self) -> str | None:
        """API key for prover when ``PROVER_PROVIDER=openai``; defaults to ``OPENAI_API_KEY``."""
        pk = self.prover_openai_api_key
        if pk is not None and str(pk).strip():
            return pk
        return self.openai_api_key

    def judge_openai_api_key_resolved(self) -> str | None:
        """API key for judge when ``JUDGE_PROVIDER`` is chutes/openai; prefers ``JUDGE_OPENAI_API_KEY``."""
        jk = (self.judge_openai_api_key or "").strip()
        if jk:
            return jk
        ok = (self.openai_api_key or "").strip()
        return ok or None

    def validator_wallet_names(self) -> tuple[str, str]:
        """Cold/hot key names for signing and metagraph (validator). Falls back to BT_WALLET_*."""
        c = (self.validator_wallet_cold or "").strip()
        h = (self.validator_wallet_hot or "").strip()
        return (c or self.wallet_cold, h or self.wallet_hot)


def normalized_judge_openai_base_url(settings: LemmaSettings) -> str:
    """Same normalization as ``judge_profile_dict`` for ``openai_base_url``."""
    return (settings.openai_base_url or "").strip().rstrip("/")


def validator_judge_stack_strict_issue(settings: LemmaSettings) -> str | None:
    """Hard subnet policy for ``lemma validator``: DeepSeek V3.2 TEE on Chutes only.

    Miners are unaffected (prover uses ``PROVER_*``); this gates scoring only.
    """
    if os.environ.get("LEMMA_FAKE_JUDGE", "").strip().lower() in ("1", "true", "yes"):
        return (
            "lemma validator requires the live Chutes judge — unset LEMMA_FAKE_JUDGE "
            "(FakeJudge cannot score miners)."
        )
    prov = (settings.judge_provider or "chutes").lower()
    if prov not in ("chutes", "openai"):
        return (
            "lemma validator requires JUDGE_PROVIDER=chutes (Chutes judge via OpenAI-compatible HTTP) with "
            f"OPENAI_MODEL={CANONICAL_JUDGE_OPENAI_MODEL!r} at {CANONICAL_JUDGE_OPENAI_BASE_URL!r} "
            f"(legacy alias openai allowed; got judge_provider={prov!r})."
        )
    got_model = (settings.openai_model or "").strip()
    if got_model != CANONICAL_JUDGE_OPENAI_MODEL:
        return (
            f"lemma validator requires OPENAI_MODEL={CANONICAL_JUDGE_OPENAI_MODEL!r} on Chutes "
            f"(got {got_model!r})."
        )
    got_base = normalized_judge_openai_base_url(settings)
    canon = CANONICAL_JUDGE_OPENAI_BASE_URL.strip().rstrip("/").lower()
    if got_base.lower() != canon:
        return (
            f"lemma validator requires OPENAI_BASE_URL={CANONICAL_JUDGE_OPENAI_BASE_URL!r} "
            f"(got {got_base!r})."
        )
    return None


def assert_validator_judge_stack_strict(settings: LemmaSettings) -> None:
    """Raise ``SystemExit`` if validator judge env is not the subnet Chutes DeepSeek stack."""
    msg = validator_judge_stack_strict_issue(settings)
    if msg:
        raise SystemExit(msg)
