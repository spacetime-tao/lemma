"""LLM prover: theorem -> reasoning trace + Submission.lean."""

from __future__ import annotations

import json
from typing import Protocol

from anthropic import AsyncAnthropic
from loguru import logger
from openai import AsyncOpenAI

from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge, ReasoningStep
from lemma.reasoning.format import format_reasoning_steps


class Prover(Protocol):
    async def solve(self, synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep] | None]:
        """Return (reasoning_trace, proof_script, optional structured steps)."""


PROVER_SYSTEM = """You are an expert Lean 4 prover. You receive a formal theorem statement.
Return ONLY a JSON object (no markdown fences) with keys:
- "reasoning_steps": array of objects, each with "text" (string, required) and optional "title" (short label).
  Use multiple steps for the informal mathematical reasoning before formalizing (PRM-style process).
- "proof_script": string, the COMPLETE contents of Submission.lean (imports + namespace Submission if used).

Alternatively you may omit reasoning_steps and provide legacy "reasoning_trace" as one string.

The proof must close the theorem with the SAME name as in the statement.
Do not use sorry, admit, or custom axioms.
"""


class LLMProver:
    def __init__(self, settings: LemmaSettings) -> None:
        self._settings = settings

    async def solve(self, synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep] | None]:
        user = f"Imports hint: {synapse.imports}\n\nTheorem block:\n{synapse.theorem_statement}\n"
        prov = (self._settings.prover_provider or "anthropic").lower()
        if prov == "openai":
            key = self._settings.openai_api_key
            if not key:
                return _stub(synapse)
            model = self._settings.prover_model or self._settings.openai_model
            okw: dict[str, object] = {"api_key": key}
            if self._settings.openai_base_url:
                okw["base_url"] = self._settings.openai_base_url
            client = AsyncOpenAI(**okw)
            resp = await client.chat.completions.create(
                model=model,
                temperature=0.3,
                messages=[
                    {"role": "system", "content": PROVER_SYSTEM},
                    {"role": "user", "content": user},
                ],
            )
            text = resp.choices[0].message.content or ""
        else:
            key = self._settings.anthropic_api_key
            if not key:
                return _stub(synapse)
            model = self._settings.prover_model or self._settings.anthropic_model
            client = AsyncAnthropic(api_key=key)
            msg = await client.messages.create(
                model=model,
                max_tokens=8192,
                system=PROVER_SYSTEM,
                messages=[{"role": "user", "content": user}],
            )
            text = ""
            for block in msg.content:
                if hasattr(block, "text"):
                    text += block.text
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
        return _normalize_prover_payload(data)


def _extract_json_obj(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no json object")
    return json.loads(text[start : end + 1])


def _normalize_prover_payload(data: dict) -> tuple[str, str, list[ReasoningStep] | None]:
    proof = str(data.get("proof_script", ""))
    raw_steps = data.get("reasoning_steps")
    steps: list[ReasoningStep] | None = None
    if isinstance(raw_steps, list) and raw_steps:
        parsed: list[ReasoningStep] = []
        for item in raw_steps:
            if isinstance(item, dict):
                parsed.append(ReasoningStep.model_validate(item))
            else:
                parsed.append(ReasoningStep(text=str(item)))
        steps = parsed
        trace = format_reasoning_steps(steps)
    else:
        trace = str(data.get("reasoning_trace", ""))
    return trace, proof, steps


def _stub(synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep] | None]:
    trace = "stub: no PROVER API key configured"
    stub_steps = [ReasoningStep(title="Setup", text=trace)]
    if "two_plus_two_eq_four" in synapse.theorem_statement:
        proof = """import Mathlib

namespace Submission

theorem two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by rfl

end Submission
"""
        steps = [
            ReasoningStep(title="Observation", text="Goal is equality of natural numbers."),
            ReasoningStep(title="Formal proof", text="Close by reflexivity (rfl)."),
        ]
        return format_reasoning_steps(steps), proof, steps
    return trace, synapse.theorem_statement, stub_steps
