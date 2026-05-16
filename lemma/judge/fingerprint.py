"""Stable fingerprints for judge prompts (consensus / upgrades)."""

from __future__ import annotations

import hashlib

import lemma.judge.prompts as prompts


def rubric_sha256() -> str:
    """SHA-256 of rubric system prompt + user template (canonical judge text)."""
    h = hashlib.sha256()
    h.update(prompts.RUBRIC_SYSTEM.encode("utf-8"))
    h.update(b"\n")
    h.update(prompts.RUBRIC_USER_TEMPLATE.encode("utf-8"))
    return h.hexdigest()
