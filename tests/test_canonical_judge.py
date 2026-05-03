"""Subnet canonical OpenAI judge model policy."""

import pytest
from lemma.common.config import (
    CANONICAL_JUDGE_OPENAI_MODEL,
    LemmaSettings,
    assert_canonical_openai_judge_model,
    canonical_openai_judge_model_issue,
)


def test_canonical_issue_none_when_model_matches() -> None:
    s = LemmaSettings(openai_model=CANONICAL_JUDGE_OPENAI_MODEL)
    assert canonical_openai_judge_model_issue(s) is None
    assert_canonical_openai_judge_model(s)


def test_canonical_issue_when_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = LemmaSettings(openai_model="other/model")
    assert canonical_openai_judge_model_issue(s) is not None
    with pytest.raises(SystemExit):
        assert_canonical_openai_judge_model(s)


def test_canonical_skipped_for_fake_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEMMA_FAKE_JUDGE", "1")
    s = LemmaSettings(openai_model="other/model")
    assert canonical_openai_judge_model_issue(s) is None


def test_canonical_allowed_when_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = LemmaSettings(openai_model="other/model", allow_noncanonical_judge_model=True)
    assert canonical_openai_judge_model_issue(s) is None


def test_canonical_skipped_for_anthropic_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = LemmaSettings(judge_provider="anthropic", openai_model="other/model")
    assert canonical_openai_judge_model_issue(s) is None
