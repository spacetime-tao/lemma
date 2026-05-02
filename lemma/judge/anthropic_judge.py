"""Anthropic Claude judge."""

from __future__ import annotations

from anthropic import AsyncAnthropic

from lemma.judge.base import RubricScore
from lemma.judge.json_util import parse_rubric_json
from lemma.judge.prompts import RUBRIC_SYSTEM, RUBRIC_USER_TEMPLATE


class AnthropicJudge:
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        *,
        temperature: float = 0.2,
        max_tokens: int = 256,
    ) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def score(self, theorem: str, trace: str, proof: str) -> RubricScore:
        user = RUBRIC_USER_TEMPLATE.format(theorem=theorem, trace=trace or "", proof=proof or "")
        msg = await self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=RUBRIC_SYSTEM,
            messages=[{"role": "user", "content": user}],
        )
        text = ""
        for block in msg.content:
            if hasattr(block, "text"):
                text += block.text
        return parse_rubric_json(text)
