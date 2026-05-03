"""Problem JSON codec for remote verify."""

from lemma.lean.problem_codec import problem_from_payload, problem_to_payload
from lemma.problems.base import Problem


def test_problem_roundtrip_minimal() -> None:
    p = Problem(
        id="t1",
        theorem_name="foo",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.22.0",
        mathlib_rev="abc123",
        imports=("Mathlib",),
        extra={"challenge_full": "import Mathlib\n\ntheorem foo : True := by sorry\n"},
    )
    d = problem_to_payload(p)
    q = problem_from_payload(d)
    assert q == p


def test_problem_roundtrip_extra_defaults() -> None:
    p = Problem(
        id="x",
        theorem_name="bar",
        type_expr="Nat",
        split="medium",
        lean_toolchain="leanprover/lean4:v4.22.0",
        mathlib_rev="deadbeef",
    )
    q = problem_from_payload(problem_to_payload(p))
    assert q.id == p.id
    assert q.extra == {}
