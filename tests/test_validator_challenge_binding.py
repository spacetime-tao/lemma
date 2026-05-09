"""Validator challenge-binding checks."""

from __future__ import annotations

import pytest
from lemma.problems.base import Problem
from lemma.protocol import LemmaChallenge
from lemma.validator.epoch import _response_matches_problem_challenge


def _problem() -> Problem:
    return Problem(
        id="gen/1",
        theorem_name="t",
        type_expr="True",
        split="easy",
        lean_toolchain="lt",
        mathlib_rev="mr",
        imports=("Mathlib",),
    )


def _response(problem: Problem) -> LemmaChallenge:
    return LemmaChallenge(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        deadline_unix=1,
        deadline_block=10,
        metronome_id="m1",
        proof_script="namespace Submission\n\ntheorem t : True := by trivial\n\nend Submission\n",
    )


def test_response_matches_current_problem_challenge() -> None:
    problem = _problem()

    assert _response_matches_problem_challenge(
        _response(problem),
        problem,
        metronome_id="m1",
        deadline_block=10,
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("theorem_id", "gen/easy"),
        ("theorem_statement", "import Mathlib\n\ntheorem easy : True := by\n  sorry\n"),
        ("imports", ["OtherImport"]),
        ("lean_toolchain", "other-toolchain"),
        ("mathlib_rev", "other-mathlib"),
        ("metronome_id", "other-round"),
        ("deadline_block", 11),
    ],
)
def test_response_rejects_challenge_field_mismatch(field: str, value: object) -> None:
    problem = _problem()
    resp = _response(problem)
    setattr(resp, field, value)

    assert not _response_matches_problem_challenge(
        resp,
        problem,
        metronome_id="m1",
        deadline_block=10,
    )

