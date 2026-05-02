"""Synapse serialization."""

from lemma.protocol import LemmaChallenge, ReasoningStep


def test_lemma_challenge_json_roundtrip() -> None:
    s = LemmaChallenge(
        theorem_id="demo/two_plus_two",
        theorem_statement="theorem two_plus_two : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        deadline_unix=123,
        metronome_id="m1",
        reasoning_trace="plan",
        reasoning_steps=[
            ReasoningStep(title="Sketch", text="Outline the proof."),
            ReasoningStep(text="Fill in Lean."),
        ],
        proof_script="import Mathlib",
    )
    s2 = LemmaChallenge.model_validate_json(s.model_dump_json())
    assert s2.theorem_id == s.theorem_id
    assert s2.metronome_id == s.metronome_id
    assert s2.reasoning_trace == "plan"
    assert s2.reasoning_steps is not None
    assert len(s2.reasoning_steps) == 2
    assert s2.reasoning_steps[0].title == "Sketch"
