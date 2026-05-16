"""Canonical validator profile fingerprint."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from lemma.common.config import LemmaSettings
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.known_theorems import known_theorems_manifest_sha256

PROFILE_SCHEMA = "lemma_cadence_profile_v5"


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
            "cadence_window_blocks": int(settings.cadence_window_blocks),
            "uid_variant_problems": bool(settings.lemma_uid_variant_problems),
        },
        "verification_policy": {
            "lean_sandbox_image": settings.lean_sandbox_image,
            "lean_sandbox_network": settings.lean_sandbox_network,
            "lean_verify_timeout_s": int(settings.lean_verify_timeout_s),
            "lean_use_docker": bool(settings.lean_use_docker),
        },
        "scoring_policy": {
            "reward_mode": "difficulty_weighted_rolling_score",
            "rolling_alpha": float(settings.lemma_scoring_rolling_alpha),
            "difficulty_weights": {
                "easy": float(settings.lemma_scoring_difficulty_easy),
                "medium": float(settings.lemma_scoring_difficulty_medium),
                "hard": float(settings.lemma_scoring_difficulty_hard),
                "extreme": float(settings.lemma_scoring_difficulty_extreme),
            },
            "coldkey_partition": bool(settings.lemma_scoring_coldkey_partition),
        },
    }


def validator_profile_sha256(settings: LemmaSettings) -> str:
    canonical = json.dumps(validator_profile_dict(settings), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
