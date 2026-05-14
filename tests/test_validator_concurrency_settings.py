"""Validator epoch concurrency caps for Lean verification."""

from lemma.common.config import LemmaSettings


def test_defaults_for_large_subnet_tuning() -> None:
    s = LemmaSettings()
    assert s.validator_poll_interval_s == 300.0
    assert s.lean_use_docker is True
    assert s.lemma_lean_verify_max_concurrent >= 1


def test_explicit_caps() -> None:
    s = LemmaSettings(
        lemma_lean_verify_max_concurrent=16,
    )
    assert s.lemma_lean_verify_max_concurrent == 16
