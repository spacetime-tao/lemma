"""Generated-template promotion gate metadata checks."""

import pytest
from lemma.problems.base import Problem
from scripts.ci_verify_generated_templates import (
    _sample_all_builders,
    _template_sample_errors,
    _validate_template_samples,
)


def test_generated_template_gate_covers_every_builder() -> None:
    samples = _sample_all_builders()
    builder_indices = [builder_index for builder_index, _, _ in samples]
    theorem_names = [p.theorem_name for _, _, p in samples]

    assert builder_indices == list(range(72))
    assert len(set(theorem_names)) == len(theorem_names)
    assert all(p.extra.get("template_fn", "").startswith("_b_") for _, _, p in samples)
    assert all(isinstance(p.extra.get("witness_proof"), str) for _, _, p in samples)


def test_generated_template_gate_rejects_bad_challenge_wiring() -> None:
    p = Problem(
        id="gen/1",
        theorem_name="expected_name",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        extra={
            "builder_index": 0,
            "template_fn": "_b_bad",
            "challenge_full": "theorem other_name : True := by\n  sorry",
        },
    )

    errors = _template_sample_errors(0, 1, p)
    assert any("challenge_full does not declare theorem_name" in err for err in errors)
    assert any("missing witness_proof" in err for err in errors)
    with pytest.raises(RuntimeError, match="generated template metadata gate failed"):
        _validate_template_samples([(0, 1, p)])


def test_generated_template_gate_rejects_incomplete_witness() -> None:
    p = Problem(
        id="gen/1",
        theorem_name="expected_name",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        extra={
            "builder_index": 0,
            "template_fn": "_b_bad",
            "challenge_full": "theorem expected_name : True := by\n  sorry",
            "solution_full": "import Mathlib\nimport Submission\n\ntheorem LemmaSubmissionBridge : True := by\n"
            "  exact Submission.expected_name\n",
            "witness_proof": "by\n  sorry",
        },
    )

    errors = _template_sample_errors(0, 1, p)
    assert any("witness_proof contains forbidden incomplete proof token" in err for err in errors)
