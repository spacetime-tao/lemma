"""Environment-driven settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import PydanticBaseSettingsSource

# Defaults for optional one-shot prose-judge tooling.
CANONICAL_JUDGE_OPENAI_MODEL = "deepseek-ai/DeepSeek-V3.2-TEE"
CANONICAL_JUDGE_OPENAI_BASE_URL = "https://llm.chutes.ai/v1"


def _stripped_or_none(value: str | None) -> str | None:
    s = (value or "").strip()
    return s or None


class LemmaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        populate_by_name=False,
    )

    def __init__(self, **data: object) -> None:
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
        """Prefer ``.env`` over process environment for the same variable name.

        Default pydantic-settings order lets exported shell variables beat values written by ``lemma-cli setup``.
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

    netuid: int = Field(default=0, ge=0, validation_alias="NETUID")

    problem_source: Literal["generated", "frozen"] = Field(
        default="generated",
        validation_alias="LEMMA_PROBLEM_SOURCE",
        description="generated = seed-expanded templates; frozen = minif2f_frozen.json catalog.",
    )
    lemma_dev_allow_frozen_problem_source: bool = Field(
        default=False,
        validation_alias="LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE",
        description=(
            "Allow LEMMA_PROBLEM_SOURCE=frozen (bundled public-eval catalog). Default false — "
            "subnet-like deployments should use generated templates."
        ),
    )
    problem_seed_quantize_blocks: int = Field(
        default=100,
        ge=1,
        le=1_000_000,
        validation_alias="LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS",
        description=(
            "Used when LEMMA_PROBLEM_SEED_MODE=quantize: problem_seed = (chain_head // N) * N "
            "(e.g. N=100 and ~12 s/block ≈ 20 min per theorem). "
            "Also subnet_epoch fallback if Tempo query fails."
        ),
    )
    problem_seed_mode: Literal["quantize", "subnet_epoch"] = Field(
        default="quantize",
        validation_alias="LEMMA_PROBLEM_SEED_MODE",
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
        validation_alias="LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS",
        description=(
            "Subtract this many blocks from RPC chain head before problem_seed resolution and forward HTTP "
            "deadline math (same value used for both). Default 0; try 1 if validators disagree on theorem by "
            "one block near quantize boundaries."
        ),
    )
    minif2f_catalog_path: Path | None = Field(
        default=None,
        validation_alias="LEMMA_MINIF2F_CATALOG_PATH",
        description="Optional path to frozen JSON array (default: bundled lemma/problems/minif2f_frozen.json).",
    )
    generated_registry_expected_sha256: str | None = Field(
        default=None,
        validation_alias="LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED",
        description=(
            "Validators with LEMMA_PROBLEM_SOURCE=generated must set this; startup fails unless it matches "
            "the live generated-registry hash (`lemma meta`)."
        ),
    )
    lemma_generated_legacy_plain_rng: bool = Field(
        default=False,
        validation_alias="LEMMA_GENERATED_LEGACY_PLAIN_RNG",
        description=(
            "If true, template RNG uses random.Random(chain_seed) (legacy). Default false: SHA256-mix chain seed "
            "before RNG for less correlated template picks across adjacent seeds (see lemma/problems/generated.py)."
        ),
    )
    subtensor_network: str = Field(
        default="finney",
        validation_alias="SUBTENSOR_NETWORK",
    )
    subtensor_chain_endpoint: str | None = Field(
        default=None,
        validation_alias="SUBTENSOR_CHAIN_ENDPOINT",
    )

    wallet_cold: str = Field(
        default="default",
        validation_alias="BT_WALLET_COLD",
    )
    wallet_hot: str = Field(
        default="default",
        validation_alias="BT_WALLET_HOT",
    )
    validator_wallet_cold: str | None = Field(
        default=None,
        validation_alias="BT_VALIDATOR_WALLET_COLD",
        description="If set, `lemma validator` / `validator-check` use this coldkey instead of BT_WALLET_COLD.",
    )
    validator_wallet_hot: str | None = Field(
        default=None,
        validation_alias="BT_VALIDATOR_WALLET_HOT",
        description="If set, validator uses this hotkey name instead of BT_WALLET_HOT.",
    )

    axon_port: int = Field(default=8091, validation_alias="AXON_PORT")
    axon_external_ip: str | None = Field(
        default=None,
        validation_alias="AXON_EXTERNAL_IP",
        description="Public IPv4/host validators use to reach this axon; set explicitly for production miners.",
    )
    axon_discover_external_ip: bool = Field(
        default=False,
        validation_alias="AXON_DISCOVER_EXTERNAL_IP",
        description="If true and AXON_EXTERNAL_IP is unset, fetch public IPv4 over HTTPS before serving.",
    )

    lean_sandbox_image: str = Field(
        default="lemma/lean-sandbox:latest",
        validation_alias="LEAN_SANDBOX_IMAGE",
        description=(
            "Docker image/ref used for Lean verification. The local default is mutable; production templates "
            "should set the subnet-published immutable tag or digest."
        ),
    )
    lean_verify_timeout_s: int = Field(
        default=300,
        ge=1,
        validation_alias="LEAN_VERIFY_TIMEOUT_S",
        description=(
            "Seconds for Docker/host lake build + axiom check per miner submission. "
            "Default 300 (5m); raise for heavy Mathlib builds if timeouts are false positives."
        ),
    )
    lean_sandbox_cpu: float = Field(
        default=2.0,
        validation_alias="LEAN_SANDBOX_CPU",
    )
    lean_sandbox_mem_mb: int = Field(
        default=8192,
        validation_alias="LEAN_SANDBOX_MEM_MB",
    )
    lean_sandbox_network: str = Field(
        default="none",
        validation_alias="LEAN_SANDBOX_NETWORK",
    )
    lean_use_docker: bool = Field(
        default=True,
        validation_alias="LEMMA_USE_DOCKER",
        description=(
            "When true (default), validators/miners/`lemma verify` use Docker for LeanSandbox — subnet parity. "
            "Set false only for host `lake` when toolchain matches `LEAN_SANDBOX_IMAGE` and policy allows."
        ),
    )
    allow_host_lean: bool = Field(
        default=False,
        validation_alias="LEMMA_ALLOW_HOST_LEAN",
        description=(
            "If true, allow `lemma verify --host-lean`, `lemma-cli try-prover --host-lean`, and "
            "`LEMMA_TRY_PROVER_HOST_VERIFY` for local debugging. Production validators should leave this false."
        ),
    )

    judge_provider: str = Field(
        default="chutes",
        validation_alias="JUDGE_PROVIDER",
        description=(
            "Optional prose-judge provider for one-shot research tooling. ``chutes`` and legacy ``openai`` "
            "use OpenAI-compatible HTTP; Anthropic is local judge tooling only. Live validator scoring is "
            "proof-only and does not read this field."
        ),
    )
    anthropic_api_key: str | None = Field(
        default=None,
        validation_alias="ANTHROPIC_API_KEY",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-20241022",
        validation_alias="ANTHROPIC_MODEL",
    )
    openai_api_key: str | None = Field(
        default=None,
        validation_alias="OPENAI_API_KEY",
        description=(
            "Legacy shared fallback for optional prose-judge tooling and OpenAI-compatible provers. "
            "Prefer JUDGE_OPENAI_API_KEY and PROVER_OPENAI_API_KEY so those keys stay separate."
        ),
    )
    judge_openai_api_key: str | None = Field(
        default=None,
        validation_alias="JUDGE_OPENAI_API_KEY",
        description=(
            "Chutes/OpenAI-compatible API key used only by optional prose-judge tooling. "
            "If unset, that tooling falls back to OPENAI_API_KEY."
        ),
    )
    openai_model: str = Field(
        default=CANONICAL_JUDGE_OPENAI_MODEL,
        validation_alias="OPENAI_MODEL",
        description=(
            f"Optional prose-judge model when JUDGE_PROVIDER is chutes or openai. Default: "
            f"{CANONICAL_JUDGE_OPENAI_MODEL!r}. Miners should use PROVER_MODEL for the prover id."
        ),
    )
    openai_base_url: str = Field(
        default=CANONICAL_JUDGE_OPENAI_BASE_URL,
        validation_alias="OPENAI_BASE_URL",
        description=(
            f"Optional prose-judge API base. Default: {CANONICAL_JUDGE_OPENAI_BASE_URL!r}. "
            "Miners may point `PROVER_OPENAI_BASE_URL` elsewhere."
        ),
    )
    judge_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        validation_alias="JUDGE_TEMPERATURE",
        description="Sampling temperature for OpenAI-compatible judges and local Anthropic judge tooling.",
    )
    judge_max_tokens: int = Field(
        default=256,
        ge=16,
        le=4096,
        validation_alias="JUDGE_MAX_TOKENS",
        description="Max completion tokens for judge responses (short JSON rubric).",
    )
    judge_llm_retry_attempts: int = Field(
        default=4,
        ge=1,
        le=32,
        validation_alias="LEMMA_JUDGE_LLM_RETRY_ATTEMPTS",
        description="Judge-only retries on 429 / timeouts / 5xx for each score() call.",
    )
    judge_llm_http_timeout_s: float | None = Field(
        default=None,
        gt=0.0,
        validation_alias="LEMMA_JUDGE_HTTP_TIMEOUT_S",
        description=(
            "If set, overrides LEMMA_LLM_HTTP_TIMEOUT_S for judge HTTP reads only "
            "(small JSON output; use a tighter cap to fail fast on stalls)."
        ),
    )
    judge_profile_expected_sha256: str | None = Field(
        default=None,
        validation_alias="JUDGE_PROFILE_SHA256_EXPECTED",
        description=(
            "Compatibility env name for the validator profile pin. Validators must set this; startup fails "
            "unless it matches live `lemma meta`."
        ),
    )
    prover_provider: str = Field(
        default="anthropic",
        validation_alias="PROVER_PROVIDER",
    )
    prover_model: str | None = Field(
        default=None,
        validation_alias="PROVER_MODEL",
        description="Miner-only model id. Use a capable reasoning model; see docs/models.md.",
    )
    prover_max_tokens: int = Field(
        default=32_768,
        ge=512,
        le=131_072,
        validation_alias="LEMMA_PROVER_MAX_TOKENS",
        description=(
            "Max completion tokens for one prover call (JSON with Submission.lean). "
            "OpenAI-compatible: sent as max_tokens. Anthropic: capped at 8192 (API limit for many models)."
        ),
    )
    prover_llm_retry_attempts: int = Field(
        default=4,
        ge=1,
        le=32,
        validation_alias="LEMMA_PROVER_LLM_RETRY_ATTEMPTS",
        description=(
            "How many times to call the prover LLM on transient errors (429, timeouts, 5xx) per forward. "
            "Backoff between tries grows (capped); raising this helps saturated gateways but uses more wall time."
        ),
    )
    prover_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        validation_alias="LEMMA_PROVER_TEMPERATURE",
        description="Sampling temperature for prover completions (OpenAI-compatible and Anthropic prover paths).",
    )
    prover_min_proof_script_chars: int = Field(
        default=0,
        ge=0,
        le=500_000,
        validation_alias="LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS",
        description=(
            "If > 0, reject JSON unless proof_script (full Submission.lean string) has at least this many "
            "characters after strip. 0 = off (default). Use to force longer formal proofs on your miner."
        ),
    )
    prover_openai_base_url: str | None = Field(
        default=None,
        validation_alias="PROVER_OPENAI_BASE_URL",
        description=(
            "Miner-only: OpenAI-compatible API base for PROVER_PROVIDER=openai. "
            "If unset, prover uses OPENAI_BASE_URL."
        ),
    )
    prover_openai_api_key: str | None = Field(
        default=None,
        validation_alias="PROVER_OPENAI_API_KEY",
        description=(
            "Miner-only: API key for the prover’s OpenAI-compatible endpoint. "
            "If unset, prover falls back to OPENAI_API_KEY."
        ),
    )

    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    # Validator — forward query (HTTP wait derived from block height × block time)
    llm_http_timeout_s: float = Field(
        default=900.0,
        gt=30.0,
        validation_alias="LEMMA_LLM_HTTP_TIMEOUT_S",
        description=(
            "HTTP read timeout for OpenAI-compatible + Anthropic prover calls and optional prose-judge tooling. "
            "Should fit inside one round’s forward wait (blocks × LEMMA_BLOCK_TIME_SEC_ESTIMATE)."
        ),
    )
    block_time_sec_estimate: float = Field(
        default=12.0,
        gt=0,
        le=60.0,
        validation_alias="LEMMA_BLOCK_TIME_SEC_ESTIMATE",
        description="Rough seconds per chain block — converts remaining blocks to forward HTTP timeout.",
    )
    forward_wait_min_s: float = Field(
        default=60.0,
        gt=0,
        validation_alias="LEMMA_FORWARD_WAIT_MIN_S",
        description="Floor for forward HTTP timeout after blocks×block-time (avoid unusably short waits).",
    )
    forward_wait_max_s: float = Field(
        default=86400.0,
        gt=0,
        validation_alias="LEMMA_FORWARD_WAIT_MAX_S",
        description="Ceiling for forward HTTP timeout (safety cap even when many blocks remain).",
    )
    miner_reject_past_deadline_block: bool = Field(
        default=True,
        validation_alias="LEMMA_MINER_REJECT_PAST_DEADLINE_BLOCK",
        description="If true, refuse axon work when chain head >= synapse.deadline_block (when set).",
    )
    timeout_scale_by_split: bool = Field(
        default=False,
        validation_alias="LEMMA_TIMEOUT_SCALE_BY_SPLIT",
        description=(
            "If true, multiply forward HTTP wait and LEAN_VERIFY_TIMEOUT_S by easy/medium/hard multipliers."
        ),
    )
    timeout_split_easy_mult: float = Field(
        default=1.0,
        ge=0.1,
        le=50.0,
        validation_alias="LEMMA_TIMEOUT_SPLIT_EASY_MULT",
    )
    timeout_split_medium_mult: float = Field(
        default=1.5,
        ge=0.1,
        le=50.0,
        validation_alias="LEMMA_TIMEOUT_SPLIT_MEDIUM_MULT",
    )
    timeout_split_hard_mult: float = Field(
        default=2.0,
        ge=0.1,
        le=50.0,
        validation_alias="LEMMA_TIMEOUT_SPLIT_HARD_MULT",
    )
    lemma_lean_verify_max_concurrent: int = Field(
        default=4,
        ge=1,
        le=128,
        validation_alias="LEMMA_LEAN_VERIFY_MAX_CONCURRENT",
        description=(
            "Max concurrent Lean sandbox.verify jobs per epoch (each may spawn Docker). "
            "Raise on large validators when many miners return proofs; lower if CPU/RAM or Docker struggles."
        ),
    )
    lean_verify_workspace_cache_dir: Path | None = Field(
        default=None,
        validation_alias="LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR",
        description=(
            "Optional directory on fast local disk to reuse a warm `.lake` per theorem template. "
            "After the first passing verify for a template, later verifies only rebuild ``Submission`` "
            "(same subnet epoch = same template for all miners). Creates subdirs; prune manually if huge."
        ),
    )
    lemma_lean_workspace_cache_include_submission_hash: bool = Field(
        default=False,
        validation_alias="LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH",
        description=(
            "If true, cache slot names include a truncated SHA256 of Submission.lean (distinct proofs never "
            "share a directory; more disk vs template-only keys). Default false."
        ),
    )
    lemma_lean_proof_metrics_enabled: bool = Field(
        default=False,
        validation_alias="LEMMA_LEAN_PROOF_METRICS",
        description=(
            "Opt-in compare-only Lean proof metrics in VerifyResult. Does not affect rewards or weights."
        ),
    )
    lemma_lean_docker_worker: str | None = Field(
        default=None,
        validation_alias="LEMMA_LEAN_DOCKER_WORKER",
        description=(
            "Name of a **running** sandbox container: Lemma uses `docker exec` instead of `docker run` per "
            "verify (much lower latency). Must bind-mount `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` — see "
            "docs/validator.md and scripts/start_lean_docker_worker.sh."
        ),
    )
    lean_verify_remote_url: str | None = Field(
        default=None,
        validation_alias="LEMMA_LEAN_VERIFY_REMOTE_URL",
        description=(
            "Optional base URL (http/https) of a dedicated Lean verify worker process "
            "(POST `/verify` JSON — see `lemma lean-worker`). When unset, verification runs in-process "
            "via `LeanSandbox` on this machine."
        ),
    )
    lean_verify_remote_bearer: str | None = Field(
        default=None,
        validation_alias="LEMMA_LEAN_VERIFY_REMOTE_BEARER",
        description=(
            "Optional shared secret; sent as ``Authorization: Bearer`` when calling "
            "``LEMMA_LEAN_VERIFY_REMOTE_URL``."
        ),
    )
    lean_verify_remote_timeout_margin_s: float = Field(
        default=30.0,
        ge=0.0,
        le=600.0,
        validation_alias="LEMMA_LEAN_VERIFY_REMOTE_TIMEOUT_MARGIN_S",
        description=(
            "Added to ``LEAN_VERIFY_TIMEOUT_S`` (per-request split scaling included) "
            "for HTTP client read timeout."
        ),
    )
    set_weights_max_retries: int = Field(
        default=3,
        ge=1,
        le=20,
        validation_alias="SET_WEIGHTS_MAX_RETRIES",
    )
    set_weights_retry_delay_s: float = Field(
        default=2.0,
        ge=0.1,
        validation_alias="SET_WEIGHTS_RETRY_DELAY_S",
    )
    empty_epoch_weights_policy: Literal["skip", "uniform"] = Field(
        default="skip",
        validation_alias="EMPTY_EPOCH_WEIGHTS_POLICY",
        description="If no miner passes verify: skip set_weights, or emit uniform weights across all UIDs.",
    )
    validator_abort_if_not_registered: bool = Field(
        default=False,
        validation_alias="VALIDATOR_ABORT_IF_NOT_REGISTERED",
        description="If true, skip epochs when this wallet has no UID on the subnet.",
    )
    training_export_jsonl: Path | None = Field(
        default=None,
        validation_alias="LEMMA_TRAINING_EXPORT_JSONL",
        description="Append one JSON object per scored miner per epoch.",
    )
    lemma_training_export_profile: Literal["full", "summary", "reasoning_only"] = Field(
        default="full",
        validation_alias="LEMMA_TRAINING_EXPORT_PROFILE",
        description=(
            "`full`: schema v1 includes proof_script, optional labels, pareto_weight. "
            "`summary`: schema v2 omits proof, labels, metrics, and weights. "
            "`reasoning_only` is accepted as a legacy alias for `summary`."
        ),
    )

    # Scoring / incentive policy (validators)
    lemma_scoring_coldkey_partition: bool = Field(
        default=True,
        validation_alias="LEMMA_SCORING_COLDKEY_PARTITION",
        description="Cap same-coldkey hotkeys to one allocation and split it among those hotkeys.",
    )
    lemma_reputation_ema_alpha: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
        validation_alias="LEMMA_REPUTATION_EMA_ALPHA",
        description="EMA smoothing for per-UID scores before Pareto weights (0 disables smoothing).",
    )
    lemma_reputation_credibility_exponent: float = Field(
        default=1.0,
        ge=0.0,
        le=4.0,
        validation_alias="LEMMA_REPUTATION_CREDIBILITY_EXPONENT",
        description=(
            "Multiply EMA-smoothed score by (verify credibility)**exponent. "
            "Exponent 0 disables the multiplier (always 1). Default 1 applies a linear credibility curve."
        ),
    )
    lemma_reputation_verify_credibility_alpha: float = Field(
        default=0.08,
        ge=0.0,
        le=1.0,
        validation_alias="LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA",
        description=(
            "EMA alpha for per-UID verify credibility (1.0 = Lean verify passed, 0.0 = failed). "
            "0 disables updates; new UIDs start at credibility 1.0."
        ),
    )
    lemma_reputation_state_path: Path | None = Field(
        default=None,
        validation_alias="LEMMA_REPUTATION_STATE_PATH",
        description="JSON file for per-UID EMA persistence (default: ~/.lemma/validator_reputation.json).",
    )
    lemma_epoch_problem_count: int = Field(
        default=1,
        ge=1,
        le=32,
        validation_alias="LEMMA_EPOCH_PROBLEM_COUNT",
        description="Number of distinct theorems sampled per validator epoch (sequential miner queries).",
    )
    lemma_commit_reveal_enabled: bool = Field(
        default=False,
        validation_alias="LEMMA_COMMIT_REVEAL_ENABLED",
        description=(
            "Two-phase challenge: validator queries commit (hash) then reveal (proof + nonce). "
            "See docs/commit-reveal.md and lemma/protocol_commit_reveal.py."
        ),
    )
    lemma_miner_verify_attest_enabled: bool = Field(
        default=False,
        validation_alias="LEMMA_MINER_VERIFY_ATTEST_ENABLED",
        description=(
            "Validators require Sr25519 attest signatures on miner responses; miners must run "
            "`LEMMA_MINER_LOCAL_VERIFY=1` and sign after local PASS. See docs/miner-verify-attest.md."
        ),
    )
    lemma_miner_verify_attest_spot_verify_fraction: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        validation_alias="LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION",
        description=(
            "Deterministic fraction of miner responses that still run full validator Lean verify "
            "(rest trusted via attest only). 1.0 = always verify (default); 0.15 ≈ 15% heavy verify."
        ),
    )
    lemma_miner_verify_attest_spot_verify_salt: str = Field(
        default="",
        validation_alias="LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT",
        description=(
            "Optional validator/operator salt mixed into attest spot-verify selection. Keep non-empty salts "
            "out of public docs; lemma meta exposes only a SHA256 fingerprint."
        ),
    )
    lemma_judge_profile_attest_enabled: bool = Field(
        default=False,
        validation_alias="LEMMA_JUDGE_PROFILE_ATTEST_ENABLED",
        description=(
            "Optional validator-profile peer check. Compatibility env/endpoint names use judge_profile; "
            "see LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS, LEMMA_JUDGE_PROFILE_ATTEST_SKIP, "
            "`lemma validator judge-attest-serve`, docs/judge-profile-attest.md."
        ),
    )
    lemma_judge_profile_attest_peer_urls: str = Field(
        default="",
        validation_alias="LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS",
        description=(
            "Comma-separated GET URLs probed when LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1 (plaintext hex or JSON "
            "with judge_profile_sha256)."
        ),
    )
    lemma_judge_profile_attest_allow_skip: bool = Field(
        default=False,
        validation_alias="LEMMA_JUDGE_PROFILE_ATTEST_SKIP",
        description=(
            "When attest is enabled, skip peer HTTP (solo / dev only). Logs as WARN at validator startup — "
            "not for production multi-validator alignment."
        ),
    )
    lemma_judge_profile_attest_http_timeout_s: float = Field(
        default=15.0,
        ge=1.0,
        le=300.0,
        validation_alias="LEMMA_JUDGE_PROFILE_ATTEST_HTTP_TIMEOUT_S",
        description="Per-URL HTTP timeout when LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1.",
    )

    # Miner — resource limits and validator gate
    miner_min_validator_stake: float = Field(
        default=0.0,
        ge=0.0,
        validation_alias="MINER_MIN_VALIDATOR_STAKE",
        description="Minimum metagraph stake (TAO) for caller hotkey; 0 disables check.",
    )
    miner_metagraph_refresh_s: float = Field(
        default=300.0,
        ge=5.0,
        validation_alias="MINER_METAGRAPH_REFRESH_S",
    )
    miner_max_concurrent_forwards: int = Field(
        default=8,
        ge=1,
        le=256,
        validation_alias="MINER_MAX_CONCURRENT_FORWARDS",
    )
    miner_max_forwards_per_day: int = Field(
        default=0,
        ge=0,
        validation_alias="MINER_MAX_FORWARDS_PER_DAY",
        description="If >0, refuse new forwards after this many successful invokes per UTC day (0=unlimited).",
    )
    miner_require_validator_permit: bool = Field(
        default=False,
        validation_alias="MINER_REQUIRE_VALIDATOR_PERMIT",
    )
    miner_priority_by_stake: bool = Field(
        default=False,
        validation_alias="MINER_PRIORITY_BY_STAKE",
        description="Use validator stake as axon priority (requires periodic metagraph sync).",
    )
    miner_log_forwards: bool = Field(
        default=False,
        validation_alias="LEMMA_MINER_LOG_FORWARDS",
        description="Log proof_script for each forward (excerpt at INFO).",
    )
    miner_forward_summary: bool = Field(
        default=True,
        validation_alias="LEMMA_MINER_FORWARD_SUMMARY",
        description=(
            "One INFO line per forward: theorem id, split, sizes, timing; optional session totals. "
            "Disable for quieter logs."
        ),
    )
    miner_forward_timeline: bool = Field(
        default=False,
        validation_alias="LEMMA_MINER_FORWARD_TIMELINE",
        description=(
            "Per forward, log three INFO lines: (1) RECEIVE with deadline vs chain head, (2) SOLVED after prover, "
            "(3) OUTCOME with local_lean or hint to enable LEMMA_MINER_LOCAL_VERIFY. "
            "Final validator proof score is not returned on the axon."
        ),
    )
    miner_local_verify: bool = Field(
        default=False,
        validation_alias="LEMMA_MINER_LOCAL_VERIFY",
        description="Run Lean sandbox on Submission.lean after prover returns (same Docker/host as validators).",
    )
    synapse_max_statement_chars: int = Field(
        default=500_000,
        ge=1024,
        validation_alias="SYNAPSE_MAX_STATEMENT_CHARS",
    )
    synapse_max_proof_chars: int = Field(
        default=500_000,
        ge=1024,
        validation_alias="SYNAPSE_MAX_PROOF_CHARS",
    )
    def prover_openai_base_url_resolved(self) -> str:
        """OpenAI-compatible base URL for the miner prover; defaults to ``OPENAI_BASE_URL``."""
        p = (self.prover_openai_base_url or "").strip()
        return p if p else (self.openai_base_url or "").strip()

    def prover_openai_api_key_resolved(self) -> str | None:
        """API key for prover when ``PROVER_PROVIDER=openai``; falls back to ``OPENAI_API_KEY``."""
        return _stripped_or_none(self.prover_openai_api_key) or _stripped_or_none(self.openai_api_key)

    def judge_openai_api_key_resolved(self) -> str | None:
        """API key for optional prose-judge tooling; prefers ``JUDGE_OPENAI_API_KEY``."""
        return _stripped_or_none(self.judge_openai_api_key) or _stripped_or_none(self.openai_api_key)

    def validator_wallet_names(self) -> tuple[str, str]:
        """Cold/hot key names for signing and metagraph (validator). Falls back to BT_WALLET_*."""
        c = (self.validator_wallet_cold or "").strip()
        h = (self.validator_wallet_hot or "").strip()
        return (c or self.wallet_cold, h or self.wallet_hot)
