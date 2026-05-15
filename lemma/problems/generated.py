"""Small deterministic cadence problem builders."""

from __future__ import annotations

import hashlib
from collections.abc import Callable

from lemma.problems.base import Problem, ProblemSource

Builder = Callable[[int, int], Problem]


def generated_registry_sha256() -> str:
    names = ",".join(builder.__name__ for builder in _BUILDERS)
    return hashlib.sha256(names.encode("utf-8")).hexdigest()


class GeneratedCadenceSource(ProblemSource):
    """Finite generated cadence batch with append-only builder ordering."""

    def __init__(self, *, count: int = 24) -> None:
        self._problems = [_problem_for_index(idx) for idx in range(max(0, int(count)))]

    def all_problems(self) -> list[Problem]:
        return list(self._problems)

    def sample(self, seed: int, split: str | None = None) -> Problem:
        if not self._problems:
            raise ValueError("generated cadence source is empty")
        return self._problems[int(seed) % len(self._problems)]

    def get(self, problem_id: str) -> Problem:
        for problem in self._problems:
            if problem.id == problem_id:
                return problem
        raise KeyError(problem_id)


def _problem_for_index(idx: int) -> Problem:
    builder_index = idx % len(_BUILDERS)
    variant = idx // len(_BUILDERS)
    return _BUILDERS[builder_index](idx, variant)


def _mk_problem(
    *,
    idx: int,
    title: str,
    theorem_name: str,
    type_expr: str,
    difficulty: str,
) -> Problem:
    challenge = f"""import Mathlib

namespace Submission

theorem {theorem_name} : {type_expr} := by
  sorry

end Submission
"""
    return Problem(
        id=f"gen/{idx:04d}",
        theorem_name=theorem_name,
        type_expr=type_expr,
        split="generated",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        imports=("Mathlib",),
        extra={
            "source_lane": "generated",
            "title": title,
            "difficulty": difficulty,
            "order": 10_000 + idx,
            "source_url": f"https://lemmasub.net/examples/cadence/{idx:04d}/",
            "challenge_full": challenge,
            "submission_stub": challenge,
        },
    )


def _b_nat_add_zero(idx: int, variant: int) -> Problem:
    n = variant + 2
    return _mk_problem(
        idx=idx,
        title=f"Adding zero to {n}",
        theorem_name=f"generated_nat_add_zero_{idx}",
        type_expr=f"({n} : Nat) + 0 = {n}",
        difficulty="cadence",
    )


def _b_nat_zero_add(idx: int, variant: int) -> Problem:
    n = variant + 3
    return _mk_problem(
        idx=idx,
        title=f"Zero plus {n}",
        theorem_name=f"generated_nat_zero_add_{idx}",
        type_expr=f"(0 : Nat) + {n} = {n}",
        difficulty="cadence",
    )


def _b_nat_mul_one(idx: int, variant: int) -> Problem:
    n = variant + 4
    return _mk_problem(
        idx=idx,
        title=f"Multiplying {n} by one",
        theorem_name=f"generated_nat_mul_one_{idx}",
        type_expr=f"({n} : Nat) * 1 = {n}",
        difficulty="cadence",
    )


def _b_nat_one_mul(idx: int, variant: int) -> Problem:
    n = variant + 5
    return _mk_problem(
        idx=idx,
        title=f"One times {n}",
        theorem_name=f"generated_nat_one_mul_{idx}",
        type_expr=f"(1 : Nat) * {n} = {n}",
        difficulty="cadence",
    )


def _b_prop_and_comm(idx: int, variant: int) -> Problem:
    return _mk_problem(
        idx=idx,
        title="Conjunction implication flip",
        theorem_name=f"generated_and_comm_{idx}",
        type_expr="∀ p q : Prop, p ∧ q → q ∧ p",
        difficulty="cadence",
    )


def _b_prop_or_comm(idx: int, variant: int) -> Problem:
    return _mk_problem(
        idx=idx,
        title="Disjunction implication flip",
        theorem_name=f"generated_or_comm_{idx}",
        type_expr="∀ p q : Prop, p ∨ q → q ∨ p",
        difficulty="cadence",
    )


_BUILDERS: tuple[Builder, ...] = (
    _b_nat_add_zero,
    _b_nat_zero_add,
    _b_nat_mul_one,
    _b_nat_one_mul,
    _b_prop_and_comm,
    _b_prop_or_comm,
)
