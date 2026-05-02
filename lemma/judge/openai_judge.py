"""OpenAI judge."""

from __future__ import annotations

from openai import AsyncOpenAI

from lemma.judge.base import RubricScore
from lemma.judge.json_util import parse_rubric_json
from lemma.judge.prompts import RUBRIC_SYSTEM, RUBRIC_USER_TEMPLATE


class OpenAIJudge:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        *,
        base_url: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 256,
    ) -> None:
        kwargs: dict[str, object] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def score(self, theorem: str, trace: str, proof: str) -> RubricScore:
        user = RUBRIC_USER_TEMPLATE.format(theorem=theorem, trace=trace or "", proof=proof or "")
        resp = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            messages=[
                {"role": "system", "content": RUBRIC_SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        text = resp.choices[0].message.content or ""
        return parse_rubric_json(text)
