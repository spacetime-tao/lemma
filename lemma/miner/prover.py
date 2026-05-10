"""LLM prover: theorem -> Submission.lean."""

from __future__ import annotations

import json
from typing import Protocol, TypeVar

import httpx
from loguru import logger
from openai import AsyncOpenAI

from lemma.common.async_llm_retry import (
    TRANSIENT_OPENAI_COMPAT,
    anthropic_async_client_cls,
    anthropic_transient_exceptions,
    async_llm_retry,
)
from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge

T = TypeVar("T")


def _httpx_timeout(settings: LemmaSettings) -> httpx.Timeout:
    """Long **read** budget for one completion; short connect so failures surface quickly."""
    read_s = float(settings.llm_http_timeout_s)
    write_s = min(600.0, max(60.0, read_s))
    return httpx.Timeout(connect=30.0, read=read_s, write=write_s, pool=30.0)


class Prover(Protocol):
    async def solve(self, synapse: LemmaChallenge) -> str:
        """Return complete ``Submission.lean`` source."""


_STUDIO_CLIENT_SUBSTR = "gen-lang-client"


def _raise_if_prover_model_is_studio_client_id(model: str | None) -> None:
    """Gemini 404s often mean PROVER_MODEL was set to an AI Studio internal id by mistake."""
    if model and _STUDIO_CLIENT_SUBSTR in model.lower():
        raise ValueError(
            "PROVER_MODEL looks like a Google AI Studio internal id (gen-lang-client-…), not a model name. "
            "Set PROVER_MODEL to a public Gemini id, e.g. gemini-2.0-flash — see "
            "https://ai.google.dev/gemini-api/docs/models"
        )


PROVER_SYSTEM = """You are an expert Lean 4 prover. The user message has only:
1. "Imports hint": suggested modules for this challenge.
2. "Theorem block": the exact Lean theorem source to prove.

Return ONLY a JSON object, with no markdown fences:
{
  "proof_script": "complete Submission.lean contents"
}

Lean contract:
- `proof_script` must be the complete `Submission.lean`: imports, `namespace Submission`, the theorem with the
  same name and statement as the challenge, and `end Submission`.
- Prove the theorem as stated; do not change the statement or add assumptions.
- This namespace is required because `Solution.lean` imports `Submission` and checks `Submission.<theorem_name>`.
- Correctness comes first. Mathlib lemmas, `simp`, `rw`, `ring`, `linarith`, `exact`, `calc`, `cases`, and induction
  are all allowed when appropriate.
- Do not use `sorry`, `admit`, `axiom`, or custom unsound declarations.
- For reversed associativity goals over Nat multiplication, use `(Nat.mul_assoc a b c).symm`, a left rewrite, or
  `symm` before `Nat.mul_assoc`.
- For Real absolute-value triangle goals, `abs_add_le a b` or `dist_triangle` with `Real.dist_eq` is usually the
  right Mathlib route after rewriting the expression into the needed shape.
- For integer absolute-value triangle goals like `|x + y| ≤ |x| + |y|`, use `abs_add_le x y`.
"""


class LLMProver:
    def __init__(self, settings: LemmaSettings) -> None:
        self._settings = settings

    async def solve(self, synapse: LemmaChallenge) -> str:
        _raise_if_prover_model_is_studio_client_id(self._settings.prover_model)
        user = f"Imports hint: {synapse.imports}\n\nTheorem block:\n{synapse.theorem_statement}\n"
        text = await self._complete(user)
        if text is None:
            return _stub(synapse)
        if self._settings.miner_log_forwards:
            tail = text if len(text) <= 16_000 else text[:8000] + "\n... [truncated] ...\n" + text[-8000:]
            logger.debug("prover raw model output:\n{}", tail)
        try:
            data = _extract_json_obj(text)
        except (json.JSONDecodeError, ValueError):
            logger.warning(
                "prover JSON parse error; raw excerpt:\n{}",
                text[:6000] if text else "<empty>",
            )
            return "-- prover JSON parse error\n"
        return _normalize_prover_payload(data, self._settings)

    async def _complete(self, user: str) -> str | None:
        prov = (self._settings.prover_provider or "anthropic").lower()
        if prov == "openai":
            return await self._complete_openai(user)
        return await self._complete_anthropic(user)

    async def _complete_openai(self, user: str) -> str | None:
        key = self._settings.prover_openai_api_key_resolved()
        if not key:
            return None
        model = self._settings.prover_model or self._settings.openai_model
        t_out = _httpx_timeout(self._settings)
        base_url = self._settings.prover_openai_base_url_resolved()

        async def _openai_call() -> str:
            async with httpx.AsyncClient(timeout=t_out) as http:
                okw: dict[str, object] = {"api_key": key, "http_client": http}
                if base_url:
                    okw["base_url"] = base_url
                client = AsyncOpenAI(**okw)
                resp = await client.chat.completions.create(
                    model=model,
                    temperature=float(self._settings.prover_temperature),
                    max_tokens=self._settings.prover_max_tokens,
                    messages=[
                        {"role": "system", "content": PROVER_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                )
            return resp.choices[0].message.content or ""

        return await async_llm_retry(
            _openai_call,
            max_attempts=int(self._settings.prover_llm_retry_attempts),
            transient_exceptions=TRANSIENT_OPENAI_COMPAT,
        )

    async def _complete_anthropic(self, user: str) -> str | None:
        key = self._settings.anthropic_api_key
        if not key:
            return None
        model = self._settings.prover_model or self._settings.anthropic_model
        t_out = _httpx_timeout(self._settings)

        async def _anthropic_call() -> str:
            AsyncAnthropic = anthropic_async_client_cls()
            client = AsyncAnthropic(api_key=key, timeout=t_out)
            # Many Claude models cap output at 8192; avoid provider errors if LEMMA_PROVER_MAX_TOKENS is higher.
            max_out = min(int(self._settings.prover_max_tokens), 8192)
            msg = await client.messages.create(
                model=model,
                max_tokens=max_out,
                temperature=float(self._settings.prover_temperature),
                system=PROVER_SYSTEM,
                messages=[{"role": "user", "content": user}],
            )
            out = ""
            for block in msg.content:
                if hasattr(block, "text"):
                    out += block.text
            return out

        return await async_llm_retry(
            _anthropic_call,
            max_attempts=int(self._settings.prover_llm_retry_attempts),
            transient_exceptions=anthropic_transient_exceptions(),
        )


def _extract_json_obj(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no json object")
    return json.loads(text[start : end + 1])


def _normalize_prover_payload(
    data: dict,
    settings: LemmaSettings | None = None,
) -> str:
    """Normalize prover JSON to the proof artifact used by live scoring."""
    proof_in = str(data.get("proof_script", ""))
    if settings is not None:
        min_proof = int(settings.prover_min_proof_script_chars or 0)
        if min_proof > 0 and len(proof_in.strip()) < min_proof:
            logger.warning(
                "prover proof_script length {} below LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS={}",
                len(proof_in.strip()),
                min_proof,
            )
            return "-- prover policy: proof_script below configured minimum\n"

    return proof_in


def _stub(synapse: LemmaChallenge) -> str:
    return synapse.theorem_statement
