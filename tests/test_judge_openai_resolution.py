"""JUDGE_OPENAI_API_KEY vs legacy OPENAI_API_KEY for the judge stack."""

from __future__ import annotations

from lemma.common.config import LemmaSettings


def test_judge_key_falls_back_to_openai_api_key() -> None:
    s = LemmaSettings.model_construct(
        judge_openai_api_key=None,
        openai_api_key="chutes",
    )
    assert s.judge_openai_api_key_resolved() == "chutes"


def test_judge_openai_api_key_preferred() -> None:
    s = LemmaSettings.model_construct(
        judge_openai_api_key="judge-only",
        openai_api_key="legacy",
    )
    assert s.judge_openai_api_key_resolved() == "judge-only"


def test_judge_key_strips_whitespace() -> None:
    s = LemmaSettings.model_construct(
        judge_openai_api_key="  x  ",
        openai_api_key=None,
    )
    assert s.judge_openai_api_key_resolved() == "x"
