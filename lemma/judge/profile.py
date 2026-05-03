"""Canonical judge runtime profile (subnet parity / anti-gaming).

Hash includes rubric text plus the active provider's model and sampling params so
operators can pin one configuration (e.g. self-hosted open weights behind an
OpenAI-compatible API) and verify all validators match.
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
        "rubric_sha256": rubric_sha256(),
        "judge_provider": stored,
        "judge_temperature": float(settings.judge_temperature),
        "judge_max_tokens": int(settings.judge_max_tokens),
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
