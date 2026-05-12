"""Canonical validator scoring profile (subnet parity / anti-gaming).

Hash includes deterministic validator settings that affect proof scoring or
response acceptance. It does not include secrets, local paths, logging,
concurrency, retry policy, or optional prose-judge tooling.
"""

from __future__ import annotations

import hashlib
import json

from lemma.common.config import LemmaSettings


def judge_profile_dict(settings: LemmaSettings) -> dict[str, object]:
    """Stable dict for hashing proof-only validator policy (no API keys)."""
    out: dict[str, object] = {
        "profile_schema": "lemma_validator_profile_v6",
        "problem_policy": {
            "problem_source": (settings.problem_source or "").strip().lower(),
            "problem_seed_mode": settings.problem_seed_mode,
            "problem_seed_quantize_blocks": int(settings.problem_seed_quantize_blocks),
            "problem_seed_chain_head_slack_blocks": int(settings.lemma_problem_seed_chain_head_slack_blocks),
            "hybrid_generated_weight": int(settings.lemma_hybrid_generated_weight),
            "hybrid_catalog_weight": int(settings.lemma_hybrid_catalog_weight),
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
            "lemma_scoring_coldkey_partition": bool(settings.lemma_scoring_coldkey_partition),
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
    return out


def judge_profile_sha256(settings: LemmaSettings) -> str:
    """SHA-256 of canonical JSON for ``lemma meta`` and optional enforcement."""
    payload = judge_profile_dict(settings)
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
