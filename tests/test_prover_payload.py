"""Prover JSON normalization for proof-only payloads."""

from __future__ import annotations

import asyncio

import pytest
from lemma.common.config import LemmaSettings
from lemma.miner.prover import LLMProver, _normalize_prover_payload, _stub
from lemma.protocol import LemmaChallenge


def test_proof_script_ok() -> None:
    proof = _normalize_prover_payload(
        {
            "proof_script": "import Mathlib\n",
        }
    )
    assert proof == "import Mathlib\n"


def test_reasoning_fields_are_ignored() -> None:
    proof = _normalize_prover_payload(
        {
            "reasoning_trace": "only legacy narrative",
            "reasoning_steps": [{"title": "A", "text": "x"}],
            "proof_script": "theorem ok := by rfl",
        }
    )
    assert proof == "theorem ok := by rfl"


def test_empty_payload_returns_empty_proof() -> None:
    assert _normalize_prover_payload({}) == ""


def test_min_proof_script_chars_enforced_when_configured() -> None:
    s = LemmaSettings().model_copy(update={"prover_min_proof_script_chars": 500})
    proof = _normalize_prover_payload({"proof_script": "short"}, s)
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
    proof = _stub(synapse)

    assert proof == synapse.theorem_statement


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

    proof = asyncio.run(LLMProver(settings).solve(synapse))

    assert proof == synapse.theorem_statement
