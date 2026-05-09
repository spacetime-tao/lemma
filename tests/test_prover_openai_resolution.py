"""PROVER_OPENAI_* overrides vs judge OPENAI_* fallbacks."""

from lemma.common.config import LemmaSettings


def test_prover_openai_defaults_follow_judge() -> None:
    s = LemmaSettings(
        openai_base_url="https://llm.chutes.ai/v1",
        prover_openai_base_url=None,
        openai_api_key="k1",
        prover_openai_api_key=None,
    )
    assert s.prover_openai_base_url_resolved() == "https://llm.chutes.ai/v1"
    assert s.prover_openai_api_key_resolved() == "k1"


def test_prover_openai_can_override_gateway_and_key() -> None:
    s = LemmaSettings(
        openai_base_url="https://llm.chutes.ai/v1",
        prover_openai_base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        openai_api_key="chutes-key",
        prover_openai_api_key="gemini-key",
    )
    assert "googleapis.com" in s.prover_openai_base_url_resolved()
    assert s.prover_openai_api_key_resolved() == "gemini-key"


def test_prover_openai_key_strips_whitespace() -> None:
    s = LemmaSettings.model_construct(
        openai_api_key=" legacy ",
        prover_openai_api_key=" prover ",
    )
    assert s.prover_openai_api_key_resolved() == "prover"

    fallback = LemmaSettings.model_construct(
        openai_api_key=" legacy ",
        prover_openai_api_key=" ",
    )
    assert fallback.prover_openai_api_key_resolved() == "legacy"
