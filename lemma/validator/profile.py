"""Canonical validator profile fingerprint."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from lemma.common.config import LemmaSettings
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.known_theorems import known_theorems_manifest_sha256

PROFILE_SCHEMA = "lemma_cadence_profile_v4"


def validator_profile_dict(settings: LemmaSettings) -> dict[str, Any]:
    return {
        "profile_schema": PROFILE_SCHEMA,
        "problem_policy": {
            "problem_source": settings.problem_source,
            "known_theorems_manifest_sha256": known_theorems_manifest_sha256(settings.known_theorems_manifest_path),
            "generated_registry_sha256": generated_registry_sha256(),
        },
        "protocol_policy": {
            "validator_poll_interval_s": float(settings.validator_poll_interval_s),
            "validator_poll_timeout_s": float(settings.validator_poll_timeout_s),
            "commit_window_blocks": int(settings.commit_window_blocks),
            "target_genesis_block": settings.target_genesis_block,
        },
        "verification_policy": {
            "lean_sandbox_image": settings.lean_sandbox_image,
            "lean_sandbox_network": settings.lean_sandbox_network,
            "lean_verify_timeout_s": int(settings.lean_verify_timeout_s),
            "lean_use_docker": bool(settings.lean_use_docker),
        },
        "scoring_policy": {
            "reward_mode": "current_epoch_observed_difficulty_with_owner_burn",
            "base_reward": "(1 - solve_fraction)^2",
            "owner_burn_uid": int(settings.owner_burn_uid),
        },
    }


def validator_profile_sha256(settings: LemmaSettings) -> str:
    canonical = json.dumps(validator_profile_dict(settings), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
