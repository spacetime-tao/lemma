"""Single-call judge construction for operator CLIs (``lemma-cli judge``, ``lemma-cli rehearsal``)."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from lemma.judge.anthropic_judge import AnthropicJudge
from lemma.judge.base import Judge, RubricScore
from lemma.judge.fake import FakeJudge
from lemma.judge.openai_judge import OpenAIJudge

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def build_judge_for_one_shot(settings: LemmaSettings) -> Judge:
    """Same stack as ``lemma-cli judge``: real judge when keys exist; ``FakeJudge`` when absent or forced."""
    if os.environ.get("LEMMA_FAKE_JUDGE") == "1":
        return FakeJudge()
    key = settings.judge_openai_api_key_resolved()
    if (settings.judge_provider or "").lower() in ("openai", "chutes") and key:
        jto = float(settings.judge_llm_http_timeout_s or settings.llm_http_timeout_s)
        return OpenAIJudge(
            key,
            settings.openai_model,
            base_url=settings.openai_base_url,
            temperature=settings.judge_temperature,
            max_tokens=settings.judge_max_tokens,
            timeout=jto,
            retry_attempts=settings.judge_llm_retry_attempts,
        )
    if settings.anthropic_api_key:
        jto = float(settings.judge_llm_http_timeout_s or settings.llm_http_timeout_s)
        return AnthropicJudge(
            settings.anthropic_api_key,
            settings.anthropic_model,
            temperature=settings.judge_temperature,
            max_tokens=settings.judge_max_tokens,
            timeout=jto,
            retry_attempts=settings.judge_llm_retry_attempts,
        )
    return FakeJudge()


async def score_rubric(settings: LemmaSettings, theorem: str, trace: str, proof: str) -> RubricScore:
    """Run one rubric call (theorem + informal trace + proof text)."""
    j = build_judge_for_one_shot(settings)
    return await j.score(theorem, trace, proof)
