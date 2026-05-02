"""Canonical judge runtime profile (subnet parity / anti-gaming).

Hash includes rubric text plus the active provider's model and sampling params so
operators can pin one configuration (e.g. self-hosted open weights behind an
OpenAI-compatible API) and verify all validators match.
"""

from __future__ import annotations

import hashlib
import json

from lemma.common.config import LemmaSettings
from lemma.judge.fingerprint import rubric_sha256


def judge_profile_dict(settings: LemmaSettings) -> dict[str, object]:
    """Stable dict for hashing (no API keys). Active provider only for model fields."""
    prov = (settings.judge_provider or "openai").lower()
    out: dict[str, object] = {
        "rubric_sha256": rubric_sha256(),
        "judge_provider": prov,
        "judge_temperature": float(settings.judge_temperature),
        "judge_max_tokens": int(settings.judge_max_tokens),
    }
    if prov == "openai":
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
