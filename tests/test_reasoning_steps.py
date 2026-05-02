"""Structured reasoning steps (PRM-style)."""

from lemma.protocol import LemmaChallenge, ReasoningStep
from lemma.reasoning.format import effective_reasoning_text, format_reasoning_steps


def test_format_reasoning_steps_numbered() -> None:
    steps = [
        ReasoningStep(title="Algebra", text="Expand (x+1)^2."),
        ReasoningStep(text="Match hypotheses with rfl."),
    ]
    out = format_reasoning_steps(steps)
    assert "Step 1 — Algebra" in out
    assert "Expand" in out
    assert "Step 2" in out


def test_effective_reasoning_prefers_steps() -> None:
    s = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        reasoning_trace="flat blob should be ignored when steps present",
        reasoning_steps=[
            ReasoningStep(title="A", text="only this counts"),
        ],
    )
    assert "only this counts" in effective_reasoning_text(s)
    assert "flat blob" not in effective_reasoning_text(s)


def test_effective_reasoning_fallback_trace() -> None:
    s = LemmaChallenge(
        theorem_id="x",
        theorem_statement="theorem p : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="t",
        mathlib_rev="m",
        deadline_unix=0,
        metronome_id="z",
        reasoning_trace="legacy narrative",
        reasoning_steps=None,
    )
    assert effective_reasoning_text(s) == "legacy narrative"
