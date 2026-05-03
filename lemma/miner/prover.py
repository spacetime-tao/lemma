"""LLM prover: theorem -> reasoning trace + Submission.lean."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Protocol, TypeVar

import httpx
from anthropic import AsyncAnthropic
from loguru import logger
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, InternalServerError, RateLimitError

from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge, ReasoningStep
from lemma.reasoning.format import format_reasoning_steps

_RETRY_EXCEPTIONS = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

T = TypeVar("T")


def _fail_fast_instead_of_retry(exc: BaseException) -> bool:
    """Do not backoff-retry when the provider says billing/quota is exhausted (won't heal quickly)."""
    msg = str(exc).lower()
    if "prepayment credits are depleted" in msg:
        return True
    if "payment required" in msg and "quota" in msg:
        return True
    return False


async def _retry_llm_call(
    factory: Callable[[], Awaitable[T]],
    *,
    max_attempts: int,
) -> T:
    """Run async factory with exponential backoff on transient HTTP/API errors."""
    n = max(1, int(max_attempts))
    last: BaseException | None = None
    for attempt in range(n):
        try:
            return await factory()
        except _RETRY_EXCEPTIONS as e:
            if _fail_fast_instead_of_retry(e):
                logger.warning("LLM error looks billing/quota-related — not retrying: {}", e)
                raise
            last = e
            if attempt >= n - 1:
                raise
            wait_s = min(90.0, 5.0 * (2**attempt))
            logger.warning(
                "LLM HTTP transient error ({}) attempt {}/{} — retry in {:.0f}s: {}",
                type(e).__name__,
                attempt + 1,
                n,
                wait_s,
                e,
            )
            await asyncio.sleep(wait_s)
    assert last is not None
    raise last


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


PROVER_SYSTEM = """You are an expert Lean 4 prover. The user message has only two parts: (1) "Imports hint"
— the suggested Mathlib/modules list for this challenge — and (2) "Theorem block" — the exact Lean source
you must prove. No other hints, labels, or hidden steps are sent; you must infer the full argument yourself.

Return ONLY a JSON object (no markdown fences) with keys:
- "reasoning_steps": array of objects, each with "text" (string, required) and optional "title" (short label).
  Give informal reasoning as a true step-by-step walkthrough: plain English, logical order, no analogies
  to unrelated real-world stories (e.g. no "think of it like shopping / sports"). Explain the mathematical
  logic directly (what each case does, what each calc line accomplishes, what definitions or lemmas mean in
  this context). In-depth is preferred over artificially short summaries; thousands of characters of
  substantive explanation are encouraged.

  Compliance (informal layer — applies even when the formal proof is one tactic or uses library lemmas):
  - Do NOT compress the narrative because the proof is "easy". Every problem gets the same standard of
    exposition: restate the goal in words, name the proof strategy, cite Mathlib lemmas by name when you
    use them, and explain how the formal proof lines realize that strategy (including direction of equalities,
    why symm/rewrite applies, etc.).
  - Avoid filler words ("clearly", "obviously", "trivially") without substantive detail; replace them with
    the actual mathematical justification.
  - Use multiple distinct steps (goal → plan → lemmas/tactics → link to the proof script). Do not collapse
    the entire informal argument into a single short paragraph.
  - Informal "text" must be plain English prose only: no LaTeX (no $...$), no raw Unicode math operators.
    You MAY use digits for concrete arithmetic (e.g. 22 + 120 = 142, or "100") instead of spelling every
    number in words — precision and readability matter more than spelling out "one hundred".
    Spell out structural relations in words when describing types and goals (e.g. "less than or equal to");
    keep Lean identifiers and tactic names in backticks when needed (e.g. `le_refl`).
- "proof_script": string, the COMPLETE contents of Submission.lean (imports + namespace Submission if used).

  Formal proof style in Submission.lean — expand; do not compress:
  - Default expectation is a **detailed, multi-step** `by` block that matches the mathematical structure. Use
    explicit `calc` chains, `induction ... with` / `cases` with named branches, and `rw` / `simp only [...]`
    steps where each non-trivial step is visible. **Do not** replace a natural multi-step argument with a
    single opaque tactic (`simp`, bare `ring`, `aesop`, one-shot `exact` of a huge lemma) when the standard
    proof would spell out cases or rewrites.
  - **Induction:** write `| zero =>` and `| succ ... ih =>` (or equivalent); state the IH in `--` comments;
    in the successor case prefer a **multi-line** `calc` or an explicit rewrite chain (e.g. Nat associativity
    style: rewrite with distributivity, apply IH, rearrange) — not one hidden `simp`.
  - **Chains of equalities:** prefer `calc` with **one principal equality per line**, citing lemmas by name
    (`Nat.mul_add`, etc.), like a textbook derivation.
  - **Comments:** use Lean line comments (`-- ...`) inside `by` before each major block explaining the case,
    the goal of the next rewrite, or what the previous line established.
  - **When is a one-liner OK?** Only when the goal is immediately definitional or a single named lemma with no
    case analysis (e.g. `rfl`, or one `exact` of a lemma that directly closes the goal). If the informal proof
    needs several conceptual steps, the formal proof must show several **visible** tactic steps.

You MUST include a non-empty "reasoning_steps" array with at least one step whose "text" is non-empty.
(Legacy single-string "reasoning_trace" is not accepted — structured steps only.)

The proof must close the theorem with the SAME name as in the statement.
Do not use sorry, admit, or custom axioms.
"""


def _prover_system_text(settings: LemmaSettings) -> str:
    """Built-in prover contract plus optional operator append (from .env)."""
    extra = (settings.prover_system_append or "").strip()
    if not extra:
        return PROVER_SYSTEM
    return PROVER_SYSTEM + "\n\n--- Operator append (LEMMA_PROVER_SYSTEM_APPEND) ---\n" + extra


class LLMProver:
    def __init__(self, settings: LemmaSettings) -> None:
        self._settings = settings

    async def solve(self, synapse: LemmaChallenge) -> tuple[str, str, list[ReasoningStep] | None]:
        _raise_if_prover_model_is_studio_client_id(self._settings.prover_model)
        user = f"Imports hint: {synapse.imports}\n\nTheorem block:\n{synapse.theorem_statement}\n"
        attempts = int(self._settings.prover_llm_retry_attempts)
        prov = (self._settings.prover_provider or "anthropic").lower()
        if prov == "openai":
            key = self._settings.openai_api_key
            if not key:
                return _stub(synapse)
            model = self._settings.prover_model or self._settings.openai_model
            t_out = _httpx_timeout(self._settings)
            sys_prompt = _prover_system_text(self._settings)

            async def _openai_call() -> str:
                async with httpx.AsyncClient(timeout=t_out) as http:
                    okw: dict[str, object] = {"api_key": key, "http_client": http}
                    if self._settings.openai_base_url:
                        okw["base_url"] = self._settings.openai_base_url
                    client = AsyncOpenAI(**okw)
                    resp = await client.chat.completions.create(
                        model=model,
                        temperature=float(self._settings.prover_temperature),
                        max_tokens=self._settings.prover_max_tokens,
                        messages=[
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": user},
                        ],
                    )
                return resp.choices[0].message.content or ""

            text = await _retry_llm_call(_openai_call, max_attempts=attempts)
        else:
            key = self._settings.anthropic_api_key
            if not key:
                return _stub(synapse)
            model = self._settings.prover_model or self._settings.anthropic_model
            t_out = _httpx_timeout(self._settings)
            sys_prompt = _prover_system_text(self._settings)

            async def _anthropic_call() -> str:
                client = AsyncAnthropic(api_key=key, timeout=t_out)
                # Many Claude models cap output at 8192; avoid provider errors if PROVER_MAX_TOKENS is higher.
                max_out = min(int(self._settings.prover_max_tokens), 8192)
                msg = await client.messages.create(
                    model=model,
                    max_tokens=max_out,
                    temperature=float(self._settings.prover_temperature),
                    system=sys_prompt,
                    messages=[{"role": "user", "content": user}],
                )
                out = ""
                for block in msg.content:
                    if hasattr(block, "text"):
                        out += block.text
                return out

            text = await _retry_llm_call(_anthropic_call, max_attempts=attempts)
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
