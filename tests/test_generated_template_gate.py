"""Generated-template promotion gate metadata checks."""

import pytest
from lemma.problems.base import Problem
from lemma.problems.generated import generated_registry_canonical_dict
from scripts.ci_verify_generated_templates import (
    _run_docker_multiplex,
    _sample_all_builders,
    _template_sample_errors,
    _validate_template_samples,
)


def test_generated_template_gate_covers_every_builder() -> None:
    samples = _sample_all_builders()
    builder_count = int(generated_registry_canonical_dict()["builder_count"])
    builder_indices = [builder_index for builder_index, _, _ in samples]
    theorem_names = [p.theorem_name for _, _, p in samples]

    assert builder_indices == list(range(builder_count))
    assert len(set(theorem_names)) == len(theorem_names)
    assert all(p.extra.get("template_fn", "").startswith("_b_") for _, _, p in samples)
    assert all(isinstance(p.extra.get("witness_proof"), str) for _, _, p in samples)
    assert all(isinstance(p.extra.get("informal_statement"), str) for _, _, p in samples)
    assert all(p.extra.get("source_lane") == "generated" for _, _, p in samples)


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
            "informal_statement": "Prove that True holds.",
            "source_lane": "generated",
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
            "informal_statement": "Prove that True holds.",
            "source_lane": "generated",
        },
    )

    errors = _template_sample_errors(0, 1, p)
    assert any("witness_proof contains forbidden incomplete proof token" in err for err in errors)


def test_docker_multiplex_failure_skips_bisect_by_default(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    p = Problem(
        id="gen/1",
        theorem_name="expected_name",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
    )

    monkeypatch.delenv("CI_TEMPLATE_BISECT_ON_FAIL", raising=False)
    monkeypatch.setattr("scripts.ci_verify_generated_templates._materialize_multiplex", lambda *a, **k: None)
    monkeypatch.setattr(
        "scripts.ci_verify_generated_templates._lake_build_only",
        lambda *a, **k: (1, "lean failure details"),
    )
    monkeypatch.setattr(
        "scripts.ci_verify_generated_templates._bisect_multiplex_failures",
        lambda *a, **k: pytest.fail("bisection should be opt-in"),
    )

    assert _run_docker_multiplex([p], "lemma-lean-sandbox:ci", witness=True) == 1

    err = capsys.readouterr().err
    assert "lean failure details" in err
    assert "CI_TEMPLATE_BISECT_ON_FAIL=1" in err


def test_docker_multiplex_failure_bisects_when_enabled(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    p = Problem(
        id="gen/1",
        theorem_name="expected_name",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
    )

    monkeypatch.setenv("CI_TEMPLATE_BISECT_ON_FAIL", "1")
    monkeypatch.setattr("scripts.ci_verify_generated_templates._materialize_multiplex", lambda *a, **k: None)
    monkeypatch.setattr(
        "scripts.ci_verify_generated_templates._lake_build_only",
        lambda *a, **k: (1, "lean failure details"),
    )
    monkeypatch.setattr(
        "scripts.ci_verify_generated_templates._bisect_multiplex_failures",
        lambda *a, **k: ["bisect detail"],
    )

    assert _run_docker_multiplex([p], "lemma-lean-sandbox:ci", witness=True) == 1

    err = capsys.readouterr().err
    assert "Bisecting multiplex subsets" in err
    assert "bisect detail" in err
