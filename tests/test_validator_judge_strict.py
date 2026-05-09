"""Validators must use DeepSeek V3.2 TEE on Chutes for judging (miners unrestricted)."""

import pytest
from lemma.common.config import (
    CANONICAL_JUDGE_OPENAI_BASE_URL,
    CANONICAL_JUDGE_OPENAI_MODEL,
    LemmaSettings,
    assert_validator_judge_stack_strict,
    normalized_judge_openai_base_url,
    validator_judge_stack_strict_issue,
)


def _strict_ok() -> LemmaSettings:
    return LemmaSettings(judge_provider="chutes")


def test_strict_ok_defaults() -> None:
    s = _strict_ok()
    assert validator_judge_stack_strict_issue(s) is None
    assert_validator_judge_stack_strict(s)


def test_strict_wrong_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = LemmaSettings(openai_model="other/model")
    assert validator_judge_stack_strict_issue(s) is not None
    with pytest.raises(SystemExit):
        assert_validator_judge_stack_strict(s)


def test_strict_wrong_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = LemmaSettings(openai_base_url="http://127.0.0.1:8000/v1")
    assert validator_judge_stack_strict_issue(s) is not None
    with pytest.raises(SystemExit):
        assert_validator_judge_stack_strict(s)


def test_strict_rejects_anthropic_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = LemmaSettings(judge_provider="anthropic", openai_model="other/model")
    assert validator_judge_stack_strict_issue(s) is not None
    with pytest.raises(SystemExit):
        assert_validator_judge_stack_strict(s)


def test_strict_rejects_fake_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEMMA_FAKE_JUDGE", "1")
    s = _strict_ok()
    assert validator_judge_stack_strict_issue(s) is not None
    with pytest.raises(SystemExit):
        assert_validator_judge_stack_strict(s)


def test_strict_ok_legacy_openai_label(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = LemmaSettings(
        judge_provider="openai",
        openai_model=CANONICAL_JUDGE_OPENAI_MODEL,
        openai_base_url=CANONICAL_JUDGE_OPENAI_BASE_URL,
    )
    assert validator_judge_stack_strict_issue(s) is None


def test_chutes_url_case_insensitive() -> None:
    s = LemmaSettings(
        openai_base_url="https://LLM.CHUTES.AI/v1",
    )
    assert validator_judge_stack_strict_issue(s) is None


def test_normalized_base_matches_profile_logic() -> None:
    s = LemmaSettings(openai_base_url=" https://llm.chutes.ai/v1/ ")
    assert normalized_judge_openai_base_url(s) == CANONICAL_JUDGE_OPENAI_BASE_URL.strip().rstrip("/")
