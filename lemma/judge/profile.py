"""Canonical validator scoring profile (subnet parity / anti-gaming).

Hash includes rubric text, the active judge stack, and deterministic validator
settings that affect scoring or response acceptance. It does not include secrets,
local paths, logging, concurrency, or retry policy.
"""

from __future__ import annotations

import hashlib
import json

from lemma.common.config import (
    CANONICAL_JUDGE_OPENAI_BASE_URL,
    CANONICAL_JUDGE_OPENAI_MODEL,
    LemmaSettings,
    normalized_judge_openai_base_url,
)
from lemma.judge.fingerprint import rubric_sha256


def judge_uses_openai_compatible_http(settings: LemmaSettings) -> bool:
    """Chutes and ``openai`` both use the OpenAI-compatible HTTP client to the configured base URL."""
    p = (settings.judge_provider or "chutes").lower()
    return p in ("openai", "chutes")


def judge_provider_for_profile_hash(settings: LemmaSettings) -> str:
    """Canonical ``judge_provider`` value stored in ``lemma meta`` / pin JSON.

    Legacy ``JUDGE_PROVIDER=openai`` with the official Chutes + DeepSeek stack is normalized to
    ``chutes`` so the fingerprint matches ``JUDGE_PROVIDER=chutes``.
    """
    p = (settings.judge_provider or "chutes").lower()
    if p == "openai":
        model_ok = (settings.openai_model or "").strip() == CANONICAL_JUDGE_OPENAI_MODEL
        base_ok = (
            normalized_judge_openai_base_url(settings).lower()
            == CANONICAL_JUDGE_OPENAI_BASE_URL.strip().rstrip("/").lower()
        )
        if model_ok and base_ok:
            return "chutes"
        return "openai"
    if p == "chutes":
        return "chutes"
    return p


def judge_profile_dict(settings: LemmaSettings) -> dict[str, object]:
    """Stable dict for hashing (no API keys). Active provider only for model fields."""
    stored = judge_provider_for_profile_hash(settings)
    out: dict[str, object] = {
        "profile_schema": "lemma_validator_profile_v3",
        "rubric_sha256": rubric_sha256(),
        "judge_provider": stored,
        "judge_temperature": float(settings.judge_temperature),
        "judge_max_tokens": int(settings.judge_max_tokens),
        "problem_policy": {
            "problem_source": (settings.problem_source or "").strip().lower(),
            "problem_seed_mode": settings.problem_seed_mode,
            "problem_seed_quantize_blocks": int(settings.problem_seed_quantize_blocks),
            "problem_seed_chain_head_slack_blocks": int(settings.lemma_problem_seed_chain_head_slack_blocks),
        },
        "verification_policy": {
            "lean_sandbox_image": (settings.lean_sandbox_image or "").strip(),
            "lean_sandbox_network": (settings.lean_sandbox_network or "").strip(),
            "lean_verify_timeout_s": int(settings.lean_verify_timeout_s),
            "block_time_sec_estimate": float(settings.block_time_sec_estimate),
            "forward_wait_min_s": float(settings.forward_wait_min_s),
            "forward_wait_max_s": float(settings.forward_wait_max_s),
            "timeout_scale_by_split": bool(settings.timeout_scale_by_split),
            "timeout_split_easy_mult": float(settings.timeout_split_easy_mult),
            "timeout_split_medium_mult": float(settings.timeout_split_medium_mult),
            "timeout_split_hard_mult": float(settings.timeout_split_hard_mult),
        },
        "scoring_policy": {
            "lemma_score_proof_weight": float(settings.lemma_score_proof_weight),
            "lemma_proof_intrinsic_strip_comments": bool(settings.lemma_proof_intrinsic_strip_comments),
            "lemma_scoring_dedup_identical": bool(settings.lemma_scoring_dedup_identical),
            "lemma_scoring_coldkey_dedup": bool(settings.lemma_scoring_coldkey_dedup),
            "lemma_reputation_ema_alpha": float(settings.lemma_reputation_ema_alpha),
            "lemma_reputation_credibility_exponent": float(settings.lemma_reputation_credibility_exponent),
            "lemma_reputation_verify_credibility_alpha": float(settings.lemma_reputation_verify_credibility_alpha),
            "lemma_epoch_problem_count": int(settings.lemma_epoch_problem_count),
            "empty_epoch_weights_policy": settings.empty_epoch_weights_policy,
        },
        "protocol_policy": {
            "lemma_commit_reveal_enabled": bool(settings.lemma_commit_reveal_enabled),
            "lemma_miner_verify_attest_enabled": bool(settings.lemma_miner_verify_attest_enabled),
            "lemma_miner_verify_attest_spot_verify_fraction": float(
                settings.lemma_miner_verify_attest_spot_verify_fraction,
            ),
            "lemma_miner_verify_attest_spot_verify_salt_sha256": hashlib.sha256(
                str(settings.lemma_miner_verify_attest_spot_verify_salt or "").encode("utf-8"),
            ).hexdigest()
            if str(settings.lemma_miner_verify_attest_spot_verify_salt or "")
            else "",
        },
    }
    if stored in ("openai", "chutes"):
        base = (settings.openai_base_url or "").strip().rstrip("/")
        out["openai_model"] = settings.openai_model
        out["openai_base_url"] = base
    else:
        out["anthropic_model"] = settings.anthropic_model
    return out


def judge_profile_sha256(settings: LemmaSettings) -> str:
    """SHA-256 of canonical JSON for ``lemma meta`` and optional enforcement."""
    payload = judge_profile_dict(settings)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
