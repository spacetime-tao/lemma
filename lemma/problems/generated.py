"""Deterministic theorem generation from an integer seed (no frozen JSON catalog).

Each validator epoch passes ``seed = current_block``; everyone expands the same seed into
the same ``Problem`` using ``random.Random(seed)`` + fixed builder ordering.

Statements are generated from **templates** so ``lake build`` stays tractable; difficulty
varies by template (easy rfl/norm_num vs heavier tactics).
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable
from dataclasses import replace
from typing import Any

from lemma.catalog.constants import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.problems.base import SOLUTION_BRIDGE_THEOREM, Problem, ProblemSource

# Taxonomy for logging / exports (not used by Lean itself).
TOPICS: tuple[str, ...] = (
    "algebra.basic",
    "algebra.ring",
    "algebra.order",
    "analysis.real_basic",
    "analysis.norm",
    "number_theory.divisibility",
    "number_theory.mod_arith",
    "combinatorics.counting",
    "combinatorics.pigeonhole_light",
    "logic.predicates",
    "logic.propositional",
    "set_theory.finite_sets",
    "topology.metric_light",
    "linear_algebra.matrix_light",
    "abstract_algebra.group_laws",
    "category_theory.trivial",
    "probability.expectation_light",
    "geometry.metric",
    "calculus.limits_light",
    "complex.basic_light",
    "graph_theory.discrete",
    "optimization.inequalities",
    "automata.regular_lite",
    "cryptography.modular",
    "foundations.recursion",
    "geometry.algebraic_light",
    "analysis.series_light",
    "number_theory.primitive_roots_light",
    "algebra.polynomial_light",
    "analysis.continuity_light",
)

Split = str  # "easy" | "medium" | "hard"

BuilderFn = Callable[[random.Random, str, int, str], Problem]


def _theorem_name(seed: int, builder_index: int) -> str:
    """Stable Lean identifier; separate builders must not collide for the same seed."""
    mix = (seed & 0xFFFFFFFF) ^ (builder_index * 1_000_003)
    return "t_" + format(abs(mix) & ((1 << 48) - 1), "x")


def _mk_problem(
    *,
    seed: int,
    topic: str,
    split: Split,
    theorem_name: str,
    type_expr: str,
    challenge_body: str,
) -> Problem:
    """Build a Problem; challenge_body is the file body after imports (single theorem + sorry)."""
    sf = f"""import Mathlib
import Submission

theorem {SOLUTION_BRIDGE_THEOREM} : {type_expr} := by
  exact Submission.{theorem_name}
"""
    extra: dict[str, Any] = {
        "challenge_full": challenge_body.strip() + "\n",
        "solution_full": sf,
        "topic": topic,
        "generator": "lemma.problems.generated",
        "seed": seed,
    }
    return Problem(
        id=f"gen/{seed}",
        theorem_name=theorem_name,
        type_expr=type_expr,
        split=split,
        lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
        mathlib_rev=DEFAULT_MATHLIB_REV,
        imports=("Mathlib",),
        extra=extra,
    )


# --- Builders: (topic_tag, split, fn). Topic tags rotate through TOPICS if unknown.


def _b_true_easy(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : True := by
  sorry"""
    return _mk_problem(seed=seed, topic=topic, split="easy", theorem_name=name, type_expr="True", challenge_body=body)


def _b_nat_add_norm_easy(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    a = rng.randint(1, 200)
    b = rng.randint(1, 200)
    lhs = a + b
    body = f"""theorem {name} : ({a} : Nat) + {b} = {lhs} := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="easy",
        theorem_name=name,
        type_expr=f"({a} : Nat) + {b} = {lhs}",
        challenge_body=body,
    )


def _b_nat_le_norm_easy(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    lo = rng.randint(0, 50)
    hi = lo + rng.randint(1, 80)
    body = f"""theorem {name} : ({lo} : Nat) ≤ {hi} := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="easy",
        theorem_name=name,
        type_expr=f"({lo} : Nat) ≤ {hi}",
        challenge_body=body,
    )


def _b_bool_and_easy(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : (true && false) = false := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="easy",
        theorem_name=name,
        type_expr="(true && false) = false",
        challenge_body=body,
    )


def _b_list_len_easy(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ([1, 2, 3] : List Nat).length = 3 := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="easy",
        theorem_name=name,
        type_expr="([1, 2, 3] : List Nat).length = 3",
        challenge_body=body,
    )


def _b_real_add_norm_easy(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    a = rng.randint(1, 20)
    b = rng.randint(1, 20)
    s = a + b
    body = f"""theorem {name} : ({a} : ℝ) + ({b} : ℝ) = ({s} : ℝ) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="easy",
        theorem_name=name,
        type_expr=f"({a} : ℝ) + ({b} : ℝ) = ({s} : ℝ)",
        challenge_body=body,
    )


def _b_forall_le_refl_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ n : Nat, n ≤ n := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ n : Nat, n ≤ n",
        challenge_body=body,
    )


def _b_add_comm_nat_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ a b : Nat, a + b = b + a := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ a b : Nat, a + b = b + a",
        challenge_body=body,
    )


def _b_mul_assoc_nat_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ a b c : Nat, a * (b * c) = (a * b) * c := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ a b c : Nat, a * (b * c) = (a * b) * c",
        challenge_body=body,
    )


def _b_sq_expand_real_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ x y : ℝ, (x + y) ^ 2 = x ^ 2 + 2 * x * y + y ^ 2 := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ x y : ℝ, (x + y) ^ 2 = x ^ 2 + 2 * x * y + y ^ 2",
        challenge_body=body,
    )


def _b_implication_true_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ P : Prop, True → P ∨ True := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ P : Prop, True → P ∨ True",
        challenge_body=body,
    )


def _b_finset_card_easy(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : (Finset.range 1).card = 1 := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="easy",
        theorem_name=name,
        type_expr="(Finset.range 1).card = 1",
        challenge_body=body,
    )


def _b_odd_square_odd_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ n : Nat, Odd n → Odd (n * n) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ n : Nat, Odd n → Odd (n * n)",
        challenge_body=body,
    )


def _b_dvd_trans_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ a b c : Nat, a ∣ b → b ∣ c → a ∣ c := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ a b c : Nat, a ∣ b → b ∣ c → a ∣ c",
        challenge_body=body,
    )


def _b_sum_range_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    n = rng.randint(2, 15)
    body = f"""theorem {name} : (∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) =
    (∑ i ∈ Finset.range ({n} + 1), (i : Nat)) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr=(
            f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) = "
            f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat))"
        ),
        challenge_body=body,
    )


def _b_exists_prime_dvd_hard(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∃ p : Nat, Nat.Prime p ∧ p ∣ 2 := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="hard",
        theorem_name=name,
        type_expr="∃ p : Nat, Nat.Prime p ∧ p ∣ 2",
        challenge_body=body,
    )


def _b_inf_many_primes_hard(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ N : Nat, ∃ p : Nat, p > N ∧ Nat.Prime p := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="hard",
        theorem_name=name,
        type_expr="∀ N : Nat, ∃ p : Nat, p > N ∧ Nat.Prime p",
        challenge_body=body,
    )


def _b_sqrt2_irrational_hard(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ¬ ∃ q : ℚ, q * q = (2 : ℚ) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="hard",
        theorem_name=name,
        type_expr="¬ ∃ q : ℚ, q * q = (2 : ℚ)",
        challenge_body=body,
    )


def _b_det_unit_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} :
    Matrix.det (!![1, 2; 3, 4] : Matrix (Fin 2) (Fin 2) ℤ) = -2 := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="Matrix.det (!![1, 2; 3, 4] : Matrix (Fin 2) (Fin 2) ℤ) = -2",
        challenge_body=body,
    )


def _b_metric_triangle_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ x y z : ℝ,
    abs (x - z) ≤ abs (x - y) + abs (y - z) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ x y z : ℝ, abs (x - z) ≤ abs (x - y) + abs (y - z)",
        challenge_body=body,
    )


def _b_continuous_id_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : Continuous (fun x : ℝ => x) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="Continuous (fun x : ℝ => x)",
        challenge_body=body,
    )


def _b_finset_union_card_hard(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} : ∀ (A B : Finset Nat), (A ∪ B).card ≤ A.card + B.card := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="hard",
        theorem_name=name,
        type_expr="∀ (A B : Finset Nat), (A ∪ B).card ≤ A.card + B.card",
        challenge_body=body,
    )


def _b_mul_add_distrib_nat_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    a, b, c = rng.randint(1, 30), rng.randint(1, 30), rng.randint(1, 30)
    body = f"""theorem {name} : ({a} + {b}) * {c} = {a} * {c} + {b} * {c} := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr=f"({a} + {b}) * {c} = {a} * {c} + {b} * {c}",
        challenge_body=body,
    )


def _b_sq_nonneg_real_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} (x : ℝ) : x * x ≥ 0 := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ x : ℝ, x * x ≥ 0",
        challenge_body=body,
    )


def _b_abs_triangle_int_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    body = f"""theorem {name} (x y : ℤ) : |x + y| ≤ |x| + |y| := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr="∀ x y : ℤ, |x + y| ≤ |x| + |y|",
        challenge_body=body,
    )


def _b_finset_filter_card_le_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    n = rng.randint(3, 24)
    body = f"""theorem {name} (P : Nat → Prop) [DecidablePred P] :
    (Finset.filter P (Finset.range {n})).card ≤ (Finset.range {n}).card := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr=f"∀ (P : Nat → Prop) [DecidablePred P], "
        f"(Finset.filter P (Finset.range {n})).card ≤ (Finset.range {n}).card",
        challenge_body=body,
    )


def _b_sum_range_succ_nat_medium(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    n = rng.randint(2, 18)
    body = f"""theorem {name} :
    (∑ i ∈ Finset.range ({n} + 1), (i : Nat)) = (∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="medium",
        theorem_name=name,
        type_expr=f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat)) = "
        f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat)",
        challenge_body=body,
    )


def _b_pow_two_mul_self_nat_hard(rng: random.Random, topic: str, seed: int, name: str) -> Problem:
    k = rng.randint(2, 9)
    body = f"""theorem {name} (m : Nat) : m ^ {k} * m = m ^ ({k} + 1) := by
  sorry"""
    return _mk_problem(
        seed=seed,
        topic=topic,
        split="hard",
        theorem_name=name,
        type_expr=f"∀ m : Nat, m ^ {k} * m = m ^ ({k} + 1)",
        challenge_body=body,
    )


def _bind_builder(builder_index: int, fn: BuilderFn) -> Callable[[random.Random, str, int], Problem]:
    """Capture builder index so theorem names stay unique per (seed, template)."""

    def _run(rng: random.Random, _unused: str, seed: int) -> Problem:
        topic = TOPICS[rng.randrange(len(TOPICS))]
        name = _theorem_name(seed, builder_index)
        p = fn(rng, topic, seed, name)
        return replace(
            p,
            extra={
                **p.extra,
                "builder_index": builder_index,
                "template_fn": fn.__name__,
            },
        )

    return _run


_RAW_BUILDERS: tuple[tuple[Split, BuilderFn], ...] = (
    ("easy", _b_true_easy),
    ("easy", _b_nat_add_norm_easy),
    ("easy", _b_nat_le_norm_easy),
    ("easy", _b_bool_and_easy),
    ("easy", _b_list_len_easy),
    ("easy", _b_real_add_norm_easy),
    ("easy", _b_finset_card_easy),
    ("medium", _b_forall_le_refl_medium),
    ("medium", _b_add_comm_nat_medium),
    ("medium", _b_mul_assoc_nat_medium),
    ("medium", _b_sq_expand_real_medium),
    ("medium", _b_implication_true_medium),
    ("medium", _b_odd_square_odd_medium),
    ("medium", _b_dvd_trans_medium),
    ("medium", _b_sum_range_medium),
    ("medium", _b_det_unit_medium),
    ("medium", _b_metric_triangle_medium),
    ("medium", _b_continuous_id_medium),
    ("hard", _b_exists_prime_dvd_hard),
    ("hard", _b_inf_many_primes_hard),
    ("hard", _b_sqrt2_irrational_hard),
    ("hard", _b_finset_union_card_hard),
    ("medium", _b_mul_add_distrib_nat_medium),
    ("medium", _b_sq_nonneg_real_medium),
    ("medium", _b_abs_triangle_int_medium),
    ("medium", _b_finset_filter_card_le_medium),
    ("medium", _b_sum_range_succ_nat_medium),
    ("hard", _b_pow_two_mul_self_nat_hard),
)

# Consensus-critical: append-only ordering; indices appear in ``_theorem_name``.
_BUILDERS: tuple[tuple[Split, Callable[[random.Random, str, int], Problem]], ...] = tuple(
    (spl, _bind_builder(i, fn)) for i, (spl, fn) in enumerate(_RAW_BUILDERS)
)


def generated_registry_canonical_dict() -> dict[str, object]:
    """Stable description of template registry (for ``lemma meta`` and optional pinning)."""
    return {
        "kind": "lemma_generated_registry_v1",
        "topics": list(TOPICS),
        "builders": [
            {"index": i, "split": spl, "fn": fn.__name__}
            for i, (spl, fn) in enumerate(_RAW_BUILDERS)
        ],
    }


def generated_registry_sha256() -> str:
    """SHA-256 of canonical JSON; changes when ``TOPICS`` or ``_RAW_BUILDERS`` order/contents change."""
    canonical = json.dumps(
        generated_registry_canonical_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GeneratedProblemSource(ProblemSource):
    """Expand ``seed`` into one theorem via deterministic RNG + template registry."""

    def all_problems(self) -> list[Problem]:
        """No finite enumeration (countably infinite id space)."""
        return []

    def sample(self, seed: int, split: str | None = None) -> Problem:
        rng = random.Random(seed)
        indices = [i for i, b in enumerate(_BUILDERS) if split is None or b[0] == split]
        if not indices:
            indices = list(range(len(_BUILDERS)))
        choice = rng.randrange(0, len(indices))
        idx = indices[choice]
        _spl, factory = _BUILDERS[idx]
        return factory(rng, "", seed)

    def get(self, problem_id: str) -> Problem:
        """Parse ``gen/<int>`` ids (same expansion as ``sample``)."""
        if not problem_id.startswith("gen/"):
            raise KeyError(problem_id)
        tail = problem_id.removeprefix("gen/").strip()
        try:
            s = int(tail, 10)
        except ValueError as e:
            raise KeyError(problem_id) from e
        return self.sample(s)
