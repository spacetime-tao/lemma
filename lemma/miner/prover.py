"""LLM prover: theorem -> reasoning trace + Submission.lean."""

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
from lemma.protocol import LemmaChallenge, ReasoningStep
from lemma.reasoning.format import format_reasoning_steps

T = TypeVar("T")


def _httpx_timeout(settings: LemmaSettings) -> httpx.Timeout:
    """Long **read** budget for one completion; short connect so failures surface quickly."""
    read_s = float(settings.llm_http_timeout_s)
    write_s = min(600.0, max(60.0, read_s))
    return httpx.Timeout(connect=30.0, read=read_s, write=write_s, pool=30.0)


class Prover(Protocol):
    async def solve(self, synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep] | None]:
        """Return (reasoning_trace, proof_script, optional structured steps)."""


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
  "reasoning_steps": [{"title": "short optional label", "text": "plain English explanation"}],
  "proof_script": "complete Submission.lean contents"
}

Reasoning contract:
- `reasoning_steps` is required. Legacy `reasoning_trace` is not accepted.
- Explain the theorem as stated: quantifiers, types, operators, and the formal goal in plain English.
- Give a real step-by-step mathematical walkthrough. Avoid filler, buzzword headings, analogies, LaTeX, and raw
  Unicode math prose. Keep Lean names or tactic names in backticks when useful.
- If the Lean proof uses a Mathlib lemma or tactic, explain what it proves and why it applies, including equality
  direction when that matters. Do not replace mathematics with meta-commentary about using a library.

Lean contract:
- `proof_script` must be the complete `Submission.lean`: imports, `namespace Submission`, the theorem with the
  same name and statement as the challenge, and `end Submission`.
- This namespace is required because `Solution.lean` imports `Submission` and checks `Submission.<theorem_name>`.
- Correctness comes first. Mathlib lemmas, `simp`, `rw`, `ring`, `linarith`, `exact`, `calc`, `cases`, and induction
  are all allowed when appropriate.
- Do not use `sorry`, `admit`, `axiom`, or custom unsound declarations.
- For reversed associativity goals over Nat multiplication, use `(Nat.mul_assoc a b c).symm`, a left rewrite, or
  `symm` before `Nat.mul_assoc`.
- For Real absolute-value triangle goals, `abs_add_le a b` or `dist_triangle` with `Real.dist_eq` is usually the
  right Mathlib route after rewriting the expression into the needed shape.
"""


class LLMProver:
    def __init__(self, settings: LemmaSettings) -> None:
        self._settings = settings

    async def solve(self, synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep] | None]:
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
            return ("parse_error", "-- prover JSON parse error\n", None)
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
            # Many Claude models cap output at 8192; avoid provider errors if PROVER_MAX_TOKENS is higher.
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


_POLICY_FAIL_TRACE = (
    "prover policy violation: JSON must contain a non-empty reasoning_steps array "
    "(at least one step with non-empty text). Legacy reasoning_trace alone is not accepted."
)
_POLICY_FAIL_PROOF = "-- prover policy: missing non-empty reasoning_steps\n"
_POLICY_FAIL_MIN_STEPS = (
    "prover policy violation: reasoning_steps has fewer entries than LEMMA_PROVER_MIN_REASONING_STEPS "
    "(informal exposition required)."
)
_POLICY_FAIL_MIN_CHARS = (
    "prover policy violation: total informal text is shorter than "
    "LEMMA_PROVER_MIN_REASONING_TOTAL_CHARS."
)
_POLICY_FAIL_MIN_PROOF_CHARS = (
    "prover policy violation: proof_script is shorter than LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS "
    "(detailed Submission.lean required)."
)


def _normalize_prover_payload(
    data: dict,
    settings: LemmaSettings | None = None,
) -> tuple[str, str, list[ReasoningStep] | None]:
    """Require structured informal reasoning; discard model proof on policy failure so verify+judge fail closed."""
    proof_in = str(data.get("proof_script", ""))
    raw_steps = data.get("reasoning_steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        logger.warning(
            "prover JSON missing non-empty reasoning_steps (legacy reasoning_trace is ignored)"
        )
        return (_POLICY_FAIL_TRACE, _POLICY_FAIL_PROOF, None)

    parsed: list[ReasoningStep] = []
    for item in raw_steps:
        if isinstance(item, dict):
            parsed.append(ReasoningStep.model_validate(item))
        else:
            parsed.append(ReasoningStep(text=str(item)))
    if not any(s.text.strip() for s in parsed):
        logger.warning("prover reasoning_steps had no non-empty text fields")
        return (_POLICY_FAIL_TRACE, _POLICY_FAIL_PROOF, None)

    if settings is not None:
        min_steps = int(settings.prover_min_reasoning_steps or 0)
        min_chars = int(settings.prover_min_reasoning_total_chars or 0)
        total_chars = sum(len(s.text.strip()) for s in parsed)
        if min_steps > 0 and len(parsed) < min_steps:
            logger.warning(
                "prover reasoning_steps count {} below LEMMA_PROVER_MIN_REASONING_STEPS={}",
                len(parsed),
                min_steps,
            )
            return (_POLICY_FAIL_MIN_STEPS, _POLICY_FAIL_PROOF, None)
        if min_chars > 0 and total_chars < min_chars:
            logger.warning(
                "prover informal reasoning length {} below LEMMA_PROVER_MIN_REASONING_TOTAL_CHARS={}",
                total_chars,
                min_chars,
            )
            return (_POLICY_FAIL_MIN_CHARS, _POLICY_FAIL_PROOF, None)

        min_proof = int(settings.prover_min_proof_script_chars or 0)
        if min_proof > 0 and len(proof_in.strip()) < min_proof:
            logger.warning(
                "prover proof_script length {} below LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS={}",
                len(proof_in.strip()),
                min_proof,
            )
            return (_POLICY_FAIL_MIN_PROOF_CHARS, _POLICY_FAIL_PROOF, None)

    trace = format_reasoning_steps(parsed)
    return trace, proof_in, parsed


def _stub(synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep] | None]:
    trace = "stub: no PROVER API key configured"
    stub_steps = [ReasoningStep(title="Setup", text=trace)]
    return trace, synapse.theorem_statement, stub_steps
