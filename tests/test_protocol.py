"""Synapse serialization."""

from lemma.protocol import (
    LemmaChallenge,
    ReasoningStep,
    synapse_miner_response_integrity_ok,
)


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


def test_body_hash_includes_proof_and_reasoning() -> None:
    common = dict(
        theorem_id="demo/two_plus_two",
        theorem_statement="theorem two_plus_two : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        deadline_unix=123,
        metronome_id="m1",
        deadline_block=None,
        reasoning_trace="plan",
        reasoning_steps=[
            ReasoningStep(title="Sketch", text="Outline the proof."),
        ],
    )
    a = LemmaChallenge(**common, proof_script="theorem a : True := rfl")
    b = LemmaChallenge(**common, proof_script="theorem b : True := rfl")
    assert a.body_hash != b.body_hash


def test_synapse_miner_response_integrity_ok_accepts_missing_response_hash() -> None:
    s = LemmaChallenge(
        theorem_id="x",
        theorem_statement="t",
        lean_toolchain="l",
        mathlib_rev="m",
        deadline_unix=1,
        deadline_block=10,
        metronome_id="mid",
        proof_script="p",
    )
    assert synapse_miner_response_integrity_ok(s) is True


def test_synapse_miner_response_integrity_ok_matches_header_hash() -> None:
    s = LemmaChallenge(
        theorem_id="x",
        theorem_statement="t",
        lean_toolchain="l",
        mathlib_rev="m",
        deadline_unix=1,
        deadline_block=10,
        metronome_id="mid",
        proof_script="p",
    )
    s2 = s.model_copy(update={"computed_body_hash": s.body_hash})
    assert synapse_miner_response_integrity_ok(s2) is True


def test_synapse_miner_response_integrity_ok_mismatch() -> None:
    s = LemmaChallenge(
        theorem_id="x",
        theorem_statement="t",
        lean_toolchain="l",
        mathlib_rev="m",
        deadline_unix=1,
        deadline_block=10,
        metronome_id="mid",
        proof_script="p",
    )
    s2 = s.model_copy(update={"computed_body_hash": "0" * 64})
    assert synapse_miner_response_integrity_ok(s2) is False


def test_synapse_miner_response_integrity_ok_rejects_missing_deadline_block() -> None:
    s = LemmaChallenge(
        theorem_id="x",
        theorem_statement="t",
        lean_toolchain="l",
        mathlib_rev="m",
        deadline_unix=1,
        deadline_block=None,
        metronome_id="mid",
        proof_script="p",
    )
    s2 = s.model_copy(update={"computed_body_hash": s.body_hash})
    assert synapse_miner_response_integrity_ok(s2) is False
