"""Prover JSON normalization — structured reasoning_steps required."""

from __future__ import annotations

import asyncio

import pytest
from lemma.common.config import LemmaSettings
from lemma.miner.prover import LLMProver, _normalize_prover_payload, _stub
from lemma.protocol import LemmaChallenge


def test_reasoning_steps_ok() -> None:
    trace, proof, steps = _normalize_prover_payload(
        {
            "reasoning_steps": [{"title": "A", "text": "x"}],
            "proof_script": "import Mathlib\n",
        }
    )
    assert proof == "import Mathlib\n"
    assert steps is not None and len(steps) == 1
    assert steps[0].title == "A"
    assert "Step 1" in trace


def test_legacy_reasoning_trace_ignored_fails_closed() -> None:
    trace, proof, steps = _normalize_prover_payload(
        {
            "reasoning_trace": "only legacy narrative",
            "proof_script": "theorem ok := by rfl",
        }
    )
    assert "reasoning_steps" in trace and "policy" in trace.lower()
    assert "prover policy" in proof
    assert steps is None


def test_empty_reasoning_steps_fails_closed() -> None:
    trace, proof, steps = _normalize_prover_payload(
        {"reasoning_steps": [], "proof_script": "ok"},
    )
    assert "policy" in trace.lower()
    assert "prover policy" in proof
    assert steps is None


def test_all_blank_step_text_fails_closed() -> None:
    trace, proof, steps = _normalize_prover_payload(
        {"reasoning_steps": [{"text": "  "}], "proof_script": "ok"},
    )
    assert steps is None
    assert "prover policy" in proof


def test_empty_payload_fails_closed() -> None:
    trace, proof, steps = _normalize_prover_payload({"proof_script": ""})
    assert steps is None
    assert "prover policy" in proof


def test_min_reasoning_steps_enforced_when_configured() -> None:
    s = LemmaSettings().model_copy(update={"prover_min_reasoning_steps": 4})
    payload = {
        "reasoning_steps": [
            {"title": "A", "text": "one"},
            {"title": "B", "text": "two"},
        ],
        "proof_script": "import Mathlib\n",
    }
    trace, proof, steps = _normalize_prover_payload(payload, s)
    assert steps is None
    assert "MIN_REASONING_STEPS" in trace


def test_min_reasoning_chars_enforced_when_configured() -> None:
    s = LemmaSettings().model_copy(update={"prover_min_reasoning_total_chars": 10_000})
    payload = {
        "reasoning_steps": [{"text": "short"}],
        "proof_script": "ok",
    }
    trace, proof, steps = _normalize_prover_payload(payload, s)
    assert steps is None
    assert "MIN_REASONING_TOTAL_CHARS" in trace


def test_min_proof_script_chars_enforced_when_configured() -> None:
    s = LemmaSettings().model_copy(update={"prover_min_proof_script_chars": 500})
    payload = {
        "reasoning_steps": [{"title": "x", "text": "enough informal text for policy"}],
        "proof_script": "short",
    }
    trace, proof, steps = _normalize_prover_payload(payload, s)
    assert steps is None
    assert "MIN_PROOF_SCRIPT_CHARS" in trace
    assert "prover policy" in proof


def test_missing_key_stub_does_not_solve_demo_theorem() -> None:
    synapse = LemmaChallenge(
        theorem_id="demo/two_plus_two",
        theorem_statement="theorem two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by\n  sorry\n",
        lean_toolchain="lean4",
        mathlib_rev="mathlib",
        deadline_unix=1,
        metronome_id="m1",
    )
    trace, proof, steps = _stub(synapse)

    assert trace == "stub: no PROVER API key configured"
    assert proof == synapse.theorem_statement
    assert steps is not None and steps[0].text == trace


@pytest.mark.parametrize("provider", ["openai", "anthropic"])
def test_llm_prover_missing_key_uses_fail_closed_stub(monkeypatch: pytest.MonkeyPatch, provider: str) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("PROVER_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    synapse = LemmaChallenge(
        theorem_id="demo/two_plus_two",
        theorem_statement="theorem two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by\n  sorry\n",
        lean_toolchain="lean4",
        mathlib_rev="mathlib",
        deadline_unix=1,
        metronome_id="m1",
    )
    settings = LemmaSettings(
        _env_file=None,
        prover_provider=provider,
        openai_api_key=None,
        prover_openai_api_key=None,
        anthropic_api_key=None,
    )

    trace, proof, steps = asyncio.run(LLMProver(settings).solve(synapse))

    assert trace == "stub: no PROVER API key configured"
    assert proof == synapse.theorem_statement
    assert steps is not None and steps[0].text == trace
