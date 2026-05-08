"""OpenAI judge."""

from __future__ import annotations

from openai import AsyncOpenAI

from lemma.common.async_llm_retry import TRANSIENT_OPENAI_COMPAT, async_llm_retry
from lemma.judge.base import RubricScore
from lemma.judge.json_util import parse_rubric_json
from lemma.judge.prompt_sanitize import sanitize_miner_fenced_block
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
        timeout: float | None = None,
        retry_attempts: int = 4,
    ) -> None:
        kwargs: dict[str, object] = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        if timeout is not None:
            kwargs["timeout"] = timeout
        self._client = AsyncOpenAI(**kwargs)
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._retry_attempts = max(1, int(retry_attempts))

    async def score(self, theorem: str, trace: str, proof: str) -> RubricScore:
        user = RUBRIC_USER_TEMPLATE.format(
            theorem=sanitize_miner_fenced_block("theorem", theorem),
            trace=sanitize_miner_fenced_block("trace", trace),
            proof=sanitize_miner_fenced_block("proof", proof),
        )

        async def _call() -> str:
            resp = await self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                messages=[
                    {"role": "system", "content": RUBRIC_SYSTEM},
                    {"role": "user", "content": user},
                ],
            )
            return resp.choices[0].message.content or ""

        text = await async_llm_retry(
            _call,
            max_attempts=self._retry_attempts,
            transient_exceptions=TRANSIENT_OPENAI_COMPAT,
        )
        return parse_rubric_json(text)
