"""Validator epoch concurrency caps (Lean verify + judge LLM)."""

from lemma.common.config import LemmaSettings


def test_defaults_for_large_subnet_tuning() -> None:
    s = LemmaSettings()
    assert s.problem_seed_quantize_blocks == 100
    assert s.lean_use_docker is True
    assert s.lemma_lean_verify_max_concurrent >= 1
    assert s.lemma_judge_max_concurrent >= 1
    assert s.lemma_lean_verify_max_concurrent <= 128
    assert s.lemma_judge_max_concurrent <= 256


def test_explicit_caps() -> None:
    s = LemmaSettings(
        lemma_lean_verify_max_concurrent=16,
        lemma_judge_max_concurrent=32,
    )
    assert s.lemma_lean_verify_max_concurrent == 16
    assert s.lemma_judge_max_concurrent == 32
