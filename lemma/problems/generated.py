"""Deterministic theorem generation from an integer seed.

Generated mode is public and deterministic: same code + same chain-aligned seed
expands to the same ``Problem``. The registry is append-only by builder index,
and the live reward path remains binary Lean verification of ``proof_script``.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import random
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any, Literal

from lemma.catalog.constants import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from lemma.problems.base import SOLUTION_BRIDGE_THEOREM, Problem, ProblemSource

Split = Literal["easy", "medium", "hard", "extreme"]

VALID_SPLITS: tuple[Split, ...] = ("easy", "medium", "hard", "extreme")
DEFAULT_SPLIT_WEIGHTS: dict[Split, int] = {"easy": 10, "medium": 35, "hard": 50, "extreme": 5}
RNG_MIX_TAG = "lemma_generated_rng_v1"

# Taxonomy for logging / exports. Templates carry their own topic; topics are no
# longer assigned randomly.
TOPICS: tuple[str, ...] = (
    "algebra.basic",
    "algebra.ring",
    "algebra.order",
    "analysis.real_basic",
    "analysis.norm",
    "analysis.continuity",
    "number_theory.divisibility",
    "number_theory.primes",
    "number_theory.mod_arith",
    "combinatorics.counting",
    "combinatorics.finite_sets",
    "logic.predicates",
    "logic.propositional",
    "set_theory.finite_sets",
    "topology.metric_light",
    "linear_algebra.matrix",
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
)


@dataclass(frozen=True)
class TemplateInstance:
    type_expr: str
    witness_proof: str
    informal_statement: str | None = None


TemplateBuilder = Callable[[random.Random], TemplateInstance]


@dataclass(frozen=True)
class GeneratedTemplate:
    split: Split
    topic: str
    family: str
    build: TemplateBuilder


GENERATED_FAMILY_STATEMENTS: dict[str, str] = {
    "nat_mul_one": "Prove that multiplying the displayed natural number by one leaves it unchanged.",
    "nat_arithmetic": "Prove that the displayed natural-number addition equals its computed value.",
    "nat_order": "Prove that the displayed natural-number inequality holds.",
    "booleans": "Prove the displayed Boolean identity.",
    "list_length": "Prove the displayed list has the stated length.",
    "list_reverse_length": "Prove that reversing a list preserves its length.",
    "real_arithmetic": "Prove that the displayed real-number addition equals its computed value.",
    "finset_range_card": "Prove that the displayed finite range has the stated cardinality.",
    "reflexive_order": "Prove that every natural number is at most itself.",
    "nat_commutativity": "Prove that addition of natural numbers commutes.",
    "nat_associativity": "Prove the displayed associativity identity for natural-number multiplication.",
    "real_polynomial_identity": "Prove the displayed polynomial identity over the real numbers.",
    "implication": "Prove the displayed elementary implication about propositions.",
    "odd_numbers": "Prove that every number of the form two times n plus one is odd.",
    "divisibility_trans": "Prove that divisibility is transitive for natural numbers.",
    "set_subset": "Prove the displayed subset fact for sets of natural numbers.",
    "finset_sum_range": "Prove the displayed identity for sums over finite ranges.",
    "matrix_det_identity": "Prove that the displayed identity matrix has determinant one.",
    "real_abs_triangle": "Prove the displayed triangle inequality for absolute value.",
    "continuous_identity": "Prove that the identity function on real numbers is continuous.",
    "prime_witness": "Prove that there is a prime number dividing two.",
    "infinite_primes": "Prove that for every bound there is a prime number at least that large.",
    "rational_square_not_two": "Prove that the displayed rational square is not two.",
    "finset_union_card": "Prove the displayed cardinality bound for a union of finite sets.",
    "set_distributivity": "Prove the displayed distributive law for set intersection and union.",
    "nat_distributivity_instance": "Prove the displayed concrete distributive identity for natural numbers.",
    "real_square_nonneg": "Prove that the square of any real number is nonnegative.",
    "integer_abs_triangle": "Prove the displayed triangle inequality for integer absolute value.",
    "finset_filter_card": "Prove that filtering a finite range cannot increase its cardinality.",
    "nat_power_identity": "Prove the displayed power identity for natural numbers.",
    "finset_insert": "Prove that inserting one natural number into the empty finite set gives cardinality one.",
    "logic_commutativity": "Prove that conjunction of propositions is commutative.",
    "nat_min_order": "Prove that the minimum of two natural numbers is at most the first number.",
    "finset_subset_card": "Prove that a finite subset has cardinality at most the larger finite set.",
    "list_append_length": "Prove that appending two lists adds their lengths.",
    "set_union_subset": "Prove that a set is contained in its union with another set.",
    "set_antisymmetry": "Prove set equality from mutual subset containment.",
    "real_affine_identity": "Prove the displayed affine identity over the real numbers.",
    "integer_monotonicity": "Prove that adding the same integer to both sides preserves order.",
    "nat_distributivity": "Prove distributivity of multiplication over addition for natural numbers.",
    "set_subset_trans": "Prove that subset containment is transitive.",
    "function_composition": "Prove associativity of function composition on natural-number functions.",
    "finset_range_membership": "Prove that a natural number belongs to the finite range ending at its successor.",
    "demorgan": "Prove the displayed De Morgan law for propositions.",
    "absolute_value": "Prove that the absolute value of a real number is nonnegative.",
    "real_cubic_identity": "Prove the displayed cubic expansion over the real numbers.",
    "integer_square_identity": "Prove the displayed difference-of-squares identity over the integers.",
    "nat_square_identity": "Prove the displayed square expansion for natural numbers.",
    "quadratic_inequality": "Prove the displayed quadratic inequality over the real numbers.",
    "four_point_abs_triangle": "Prove the displayed multi-step triangle inequality for real absolute value.",
    "sum_squares_nonneg": "Prove that the displayed sum of real squares is nonnegative.",
    "square_difference_nonneg": "Prove that the square of a real-number difference is nonnegative.",
    "set_union_inter_distrib": "Prove the displayed distributive law for set union and intersection.",
    "set_difference": "Prove the displayed identity for set difference over a union.",
    "image_preimage": "Prove that a set is contained in the preimage of its image under a function.",
    "set_image_subset_chain": "Prove that image preserves a two-step subset chain under a function.",
    "logic_curry": "Prove the displayed currying equivalence for propositions.",
    "contrapositive": "Prove the displayed contrapositive implication.",
    "divisibility_sum_squares": "Prove that divisibility is preserved by the displayed sum of squares.",
    "divisibility_three_squares": "Prove that divisibility is preserved by the displayed three-square sum.",
    "divisibility_linear_combo": "Prove that divisibility is preserved by the displayed symmetric linear combination.",
    "prime_beyond_shift": "Prove that beyond every shifted bound there is a prime number.",
    "list_reverse_append": "Prove that reversing an appended list reverses the parts in opposite order.",
    "list_map_reverse_append": "Prove the displayed identity combining list append, map, and reverse.",
    "list_map_reverse": "Prove that mapping over a list commutes with reversing it.",
    "list_replicate_append": "Prove the displayed length identity for appended replicated lists.",
    "finset_range_subset": "Prove that a smaller finite range is contained in a larger finite range.",
    "finset_card_range": "Prove the displayed cardinality identity for a finite range.",
    "finset_sum_range_two_steps": "Prove the displayed finite-sum identity by adding two successive range endpoints.",
    "matrix_transpose": "Prove that transposing a matrix twice gives the original matrix.",
    "matrix_add_zero": "Prove that adding zero to the displayed matrix gives the same matrix.",
    "continuous_polynomial": "Prove that the displayed polynomial function over real numbers is continuous.",
    "group_inverse": "Prove the inverse-of-product identity in any group.",
    "nat_add_zero_induction": "Prove by induction that adding zero on the right leaves a natural number unchanged.",
    "list_append_nil_induction": "Prove by induction that appending the empty list leaves a list unchanged.",
    "nat_mod_concrete": "Prove the displayed concrete modular-arithmetic identity.",
    "predicate_exists": "Prove that a universally true predicate holds for at least one natural number.",
    "symmetric_relation": "Prove that a symmetric relation can be used in the reversed direction.",
    "nat_rec_counter": "Prove that a simple recursive natural-number counter returns its input.",
    "set_image_mono": "Prove that image preserves subset containment under a function.",
    "real_quadratic_param": "Prove the displayed parameterized quadratic identity over the real numbers.",
    "nat_sub_self": "Prove that subtracting a natural number from itself gives zero.",
    "boolean_or": "Prove the displayed Boolean OR identity.",
    "list_cons_length": "Prove that adding one element to the front of a list increases its length by one.",
    "even_shift": "Prove that the displayed family of natural numbers is even.",
    "finset_insert_membership": "Prove that a value belongs to the finite set formed by inserting it.",
    "set_union_comm": "Prove that union of sets is commutative.",
    "real_shifted_square_lower_bound": "Prove the displayed lower bound from nonnegativity of a square.",
    "set_image_union": "Prove that image distributes over union.",
    "midpoint_identity": "Prove the displayed midpoint identity over the real numbers.",
    "finite_average_identity": "Prove the displayed finite-average identity over the real numbers.",
    "difference_quotient": "Prove the displayed difference-quotient identity over the real numbers.",
    "finite_constant_series": "Prove the displayed finite constant-sum identity.",
    "simple_graph_symmetry": "Prove the displayed symmetry fact for adjacency in a simple graph.",
    "linear_diophantine_witness": "Prove that the displayed integer linear equation has a witness.",
    "amgm_square_inequality": "Prove the displayed square-based inequality over the real numbers.",
}


def expand_seed_for_problem_rng(seed: int) -> int:
    """Deterministic 64-bit stir for ``random.Random``."""
    digest = hashlib.sha256(f"{RNG_MIX_TAG}|{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _theorem_name(seed: int, builder_index: int) -> str:
    """Stable Lean identifier; separate builders must not collide for the same seed."""
    mix = (seed & 0xFFFFFFFF) ^ (builder_index * 1_000_003)
    return "t_" + format(abs(mix) & ((1 << 48) - 1), "x")


def _inst(type_expr: str, proof: str, *, informal_statement: str | None = None) -> TemplateInstance:
    return TemplateInstance(
        type_expr=type_expr.strip(),
        witness_proof=proof.strip(),
        informal_statement=informal_statement.strip() if informal_statement else None,
    )


def _theorem_decl(name: str, type_expr: str, proof: str) -> str:
    return f"theorem {name} : {type_expr} := {proof.strip()}"


def generated_witness_submission_source(problem: Problem) -> str:
    """Public witness ``Submission.lean`` for CI template promotion gates."""
    proof = problem.extra.get("witness_proof")
    if not isinstance(proof, str) or not proof.strip():
        raise ValueError(f"problem {problem.id} has no witness_proof")
    return (
        "import Mathlib\n\n"
        "namespace Submission\n\n"
        f"{_theorem_decl(problem.theorem_name, problem.type_expr, proof)}\n\n"
        "end Submission\n"
    )


def _mk_problem(
    *,
    seed: int,
    topic: str,
    family: str,
    split: Split,
    theorem_name: str,
    instance: TemplateInstance,
) -> Problem:
    """Build a generated problem from one template instance."""
    challenge_body = _theorem_decl(theorem_name, instance.type_expr, "by\n  sorry")
    solution_full = f"""import Mathlib
import Submission

theorem {SOLUTION_BRIDGE_THEOREM} : {instance.type_expr} := by
  exact Submission.{theorem_name}
"""
    extra: dict[str, Any] = {
        "challenge_full": challenge_body.strip() + "\n",
        "solution_full": solution_full,
        "witness_proof": instance.witness_proof,
        "topic": topic,
        "family": family,
        "informal_statement": instance.informal_statement or GENERATED_FAMILY_STATEMENTS[family],
        "source_lane": "generated",
        "generator": "lemma.problems.generated",
        "seed": seed,
    }
    return Problem(
        id=f"gen/{seed}",
        theorem_name=theorem_name,
        type_expr=instance.type_expr,
        split=split,
        lean_toolchain=DEFAULT_LEAN_TOOLCHAIN,
        mathlib_rev=DEFAULT_MATHLIB_REV,
        imports=("Mathlib",),
        extra=extra,
    )


# --- Existing builders 0..39. Keep indices stable; append new templates only.


def _b_nat_mul_one_easy(rng: random.Random) -> TemplateInstance:
    n = rng.randint(1, 500)
    if rng.choice((False, True)):
        return _inst(
            f"1 * ({n} : Nat) = {n}",
            "by\n  norm_num",
            informal_statement=f"Prove that one times {n} leaves it unchanged.",
        )
    return _inst(
        f"({n} : Nat) * 1 = {n}",
        "by\n  norm_num",
        informal_statement=f"Prove that multiplying {n} by one leaves it unchanged.",
    )


def _b_nat_add_norm_easy(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 200)
    b = rng.randint(1, 200)
    if rng.choice((False, True)):
        return _inst(
            f"({a} : Nat) * {b} = {a * b}",
            "by\n  norm_num",
            informal_statement=f"Prove the natural-number multiplication {a} * {b} = {a * b}.",
        )
    return _inst(
        f"({a} : Nat) + {b} = {a + b}",
        "by\n  norm_num",
        informal_statement=f"Prove the natural-number addition {a} + {b} = {a + b}.",
    )


def _b_nat_le_norm_easy(rng: random.Random) -> TemplateInstance:
    lo = rng.randint(0, 50)
    hi = lo + rng.randint(1, 80)
    if rng.choice((False, True)):
        return _inst(
            f"({lo} : Nat) < {hi}",
            "by\n  norm_num",
            informal_statement=f"Prove that {lo} is strictly less than {hi}.",
        )
    return _inst(
        f"({lo} : Nat) ≤ {hi}",
        "by\n  norm_num",
        informal_statement=f"Prove that {lo} is at most {hi}.",
    )


def _b_bool_and_easy(rng: random.Random) -> TemplateInstance:
    left = rng.choice((True, False))
    right = rng.choice((True, False))
    result = left and right
    l_txt = str(left).lower()
    r_txt = str(right).lower()
    out_txt = str(result).lower()
    return _inst(
        f"({l_txt} && {r_txt}) = {out_txt}",
        "by\n  rfl",
        informal_statement=f"Prove the Boolean identity {l_txt} AND {r_txt} = {out_txt}.",
    )


def _b_list_len_easy(rng: random.Random) -> TemplateInstance:
    values = [rng.randint(1, 40) for _ in range(rng.randint(2, 5))]
    items = ", ".join(str(v) for v in values)
    return _inst(
        f"([{items}] : List Nat).length = {len(values)}",
        "by\n  rfl",
        informal_statement=f"Prove that the displayed list has length {len(values)}.",
    )


def _b_list_reverse_len_easy(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 40)
    b = rng.randint(1, 40)
    c = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"([{a}, {b}, {c}] : List Nat).reverse.length = ([{a}, {b}, {c}] : List Nat).length",
            "by\n  simp",
            informal_statement=f"Prove that reversing the list [{a}, {b}, {c}] keeps the same length.",
        )
    return _inst(
        f"([{a}, {b}, {c}] : List Nat).reverse.length = 3",
        "by\n  simp",
        informal_statement=f"Prove that reversing the list [{a}, {b}, {c}] preserves its length.",
    )


def _b_real_add_norm_easy(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 20)
    b = rng.randint(1, 20)
    if rng.choice((False, True)):
        return _inst(
            f"({a} : ℝ) * ({b} : ℝ) = ({a * b} : ℝ)",
            "by\n  norm_num",
            informal_statement=f"Prove the real-number multiplication {a} * {b} = {a * b}.",
        )
    return _inst(
        f"({a} : ℝ) + ({b} : ℝ) = ({a + b} : ℝ)",
        "by\n  norm_num",
        informal_statement=f"Prove the real-number addition {a} + {b} = {a + b}.",
    )


def _b_finset_card_easy(rng: random.Random) -> TemplateInstance:
    n = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"(Finset.range ({n} + 1)).card = {n} + 1",
            "by\n  simp",
            informal_statement=f"Prove that the finite range below {n + 1} has {n + 1} elements.",
        )
    return _inst(
        f"(Finset.range {n}).card = {n}",
        "by\n  simp",
        informal_statement=f"Prove that the finite range below {n} has {n} elements.",
    )


def _b_forall_le_refl_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 80)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, n + {k} = n + {k}",
            "by\n  intro n\n  rfl",
            informal_statement=f"Prove that every natural number shifted by {k} equals itself.",
        )
    return _inst(
        f"∀ n : Nat, n + {k} ≤ n + {k}",
        "by\n  intro n\n  exact le_rfl",
        informal_statement=f"Prove that every natural number shifted by {k} is at most itself.",
    )


def _b_list_reverse_length_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ xs : List Nat, (xs.map (fun n => n + {k})).length = xs.length",
            "by\n  intro xs\n  simp",
            informal_statement=f"Prove that adding {k} to every list entry preserves length.",
        )
    return _inst(
        f"∀ xs : List Nat, (xs.map (fun n => n + {k})).reverse.length = xs.length",
        "by\n  intro xs\n  simp",
        informal_statement=f"Prove that adding {k} to every list entry and reversing preserves length.",
    )


def _b_add_comm_nat_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b : Nat, {k} + a + b = {k} + b + a",
            "by\n  intro a b\n  omega",
            informal_statement=f"Prove commutativity of natural-number addition after starting with {k}.",
        )
    return _inst(
        f"∀ a b : Nat, a + b + {k} = b + a + {k}",
        "by\n  intro a b\n  omega",
        informal_statement=f"Prove commutativity of natural-number addition after adding {k} to both sides.",
    )


def _b_mul_assoc_nat_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(2, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b c : Nat, (a * b) * c * {k} = a * (b * c) * {k}",
            "by\n  intro a b c\n  ring",
            informal_statement=f"Prove associativity of natural-number multiplication before scaling by {k}.",
        )
    return _inst(
        f"∀ a b c : Nat, {k} * (a * (b * c)) = {k} * ((a * b) * c)",
        "by\n  intro a b c\n  ring",
        informal_statement=f"Prove associativity of natural-number multiplication after scaling by {k}.",
    )


def _b_sq_expand_real_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℝ, (x - y) ^ 2 + ({k} : ℝ) = x ^ 2 - 2 * x * y + y ^ 2 + ({k} : ℝ)",
            "by\n  intro x y\n  ring",
            informal_statement=f"Prove the square expansion for x minus y with {k} added to both sides.",
        )
    return _inst(
        f"∀ x y : ℝ, (x + y) ^ 2 + ({k} : ℝ) = x ^ 2 + 2 * x * y + y ^ 2 + ({k} : ℝ)",
        "by\n  intro x y\n  ring",
        informal_statement=f"Prove the square expansion over real numbers with {k} added to both sides.",
    )


def _b_implication_true_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 80)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, n ≤ {k} → n ≤ {k + 1}",
            "by\n  intro n h\n  omega",
            informal_statement=f"Prove that a natural number at most {k} is also at most {k + 1}.",
        )
    return _inst(
        f"∀ n : Nat, n = {k} → n ≤ {k + 1}",
        "by\n  intro n h\n  omega",
        informal_statement=f"Prove that if a natural number equals {k}, then it is at most {k + 1}.",
    )


def _b_odd_square_odd_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(0, 40)
    odd_tail = 2 * k + 1
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, Odd ({odd_tail} + 2 * n)",
            f"by\n  intro n\n  use n + {k}\n  ring",
            informal_statement=f"Prove that every number of the form {odd_tail} plus two times n is odd.",
        )
    return _inst(
        f"∀ n : Nat, Odd (2 * n + {odd_tail})",
        f"by\n  intro n\n  use n + {k}\n  ring",
        informal_statement=f"Prove that every number of the form two times n plus {odd_tail} is odd.",
    )


def _b_dvd_trans_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b c : Nat, a ∣ b → b ∣ c → a ∣ {k} * c",
            f"by\n  intro a b c hab hbc\n  exact dvd_mul_of_dvd_right (dvd_trans hab hbc) {k}",
            informal_statement=f"Prove transitive divisibility after multiplying by {k} on the left.",
        )
    return _inst(
        f"∀ a b c : Nat, a ∣ b → b ∣ c → a ∣ c * {k}",
        f"by\n  intro a b c hab hbc\n  exact dvd_mul_of_dvd_left (dvd_trans hab hbc) {k}",
        informal_statement=f"Prove that divisibility is transitive, then preserved after multiplying by {k}.",
    )


def _b_set_inter_subset_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B : Set (Fin {n}), A ∩ B ⊆ B",
            "by\n  intro A B x hx\n  exact hx.2",
            informal_statement=f"Prove that an intersection of sets over Fin {n} is contained in the second set.",
        )
    return _inst(
        f"∀ A B : Set (Fin {n}), A ∩ B ⊆ A",
        "by\n  intro A B x hx\n  exact hx.1",
        informal_statement=f"Prove that an intersection of sets over Fin {n} is contained in the first set.",
    )


def _b_sum_range_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 15)
    if rng.choice((False, True)):
        return _inst(
            f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat)) = "
            f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat)",
            "by\n  exact Finset.sum_range_succ (fun i : Nat => (i : Nat)) "
            f"{n}",
            informal_statement=f"Prove the finite-sum range successor identity at endpoint {n}.",
        )
    return _inst(
        f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) = "
        f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat))",
        "by\n  exact (Finset.sum_range_succ (fun i : Nat => (i : Nat)) "
        f"{n}).symm",
        informal_statement=f"Prove the finite-sum range step at endpoint {n}.",
    )


def _b_exists_prime_dvd_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    n = 2 * k
    if rng.choice((False, True)):
        return _inst(
            f"∃ p : Nat, Nat.Prime p ∧ p ∣ {n} * {n + 2}",
            "by\n  refine ⟨2, Nat.prime_two, ?_⟩\n  norm_num",
            informal_statement=f"Prove that some prime number divides {n} times {n + 2}.",
        )
    return _inst(
        f"∃ p : Nat, Nat.Prime p ∧ p ∣ {n}",
        "by\n  refine ⟨2, Nat.prime_two, ?_⟩\n  norm_num",
        informal_statement=f"Prove that some prime number divides {n}.",
    )


def _b_inf_many_primes_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            "∀ N : Nat, ∃ p : Nat, N ≤ p ∧ Nat.Prime p",
            "by\n  intro N\n  exact Nat.exists_infinite_primes N",
            informal_statement="Prove that beyond every natural-number bound there is a prime number.",
        )
    return _inst(
        f"∀ N : Nat, ∃ p : Nat, N + {k} ≤ p ∧ Nat.Prime p",
        f"by\n  intro N\n  exact Nat.exists_infinite_primes (N + {k})",
        informal_statement=f"Prove that beyond every bound shifted by {k}, there is a prime number.",
    )


def _b_rational_square_not_two_hard(rng: random.Random) -> TemplateInstance:
    n = rng.choice((0, 1, 3, 4, 5, 6, 7, 8, 9, 10))
    if rng.choice((False, True)):
        return _inst(
            f"({n} : ℚ) ^ 2 ≠ 2",
            "by\n  norm_num",
            informal_statement=f"Prove that the rational square {n} squared is not two.",
        )
    return _inst(
        f"({n} : ℚ) * ({n} : ℚ) ≠ 2",
        "by\n  norm_num",
        informal_statement=f"Prove that the rational square {n} times {n} is not two.",
    )


def _b_det_unit_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 4)
    if rng.choice((False, True)):
        return _inst(
            f"Matrix.det (1 : Matrix (Fin {n}) (Fin {n}) ℚ) = 1",
            "by\n  simp",
            informal_statement=f"Prove that the {n} by {n} rational identity matrix has determinant one.",
        )
    return _inst(
        f"Matrix.det (1 : Matrix (Fin {n}) (Fin {n}) ℤ) = 1",
        "by\n  simp",
        informal_statement=f"Prove that the {n} by {n} identity matrix has determinant one.",
    )


def _b_metric_triangle_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            "∀ x y z : ℝ, |x - z| ≤ |x - y| + |y - z|",
            "by\n  intro x y z\n  have h : x - z = (x - y) + (y - z) := by\n    ring\n  "
            "calc\n    |x - z| = |(x - y) + (y - z)| := by rw [h]\n    "
            "_ ≤ |x - y| + |y - z| := abs_add_le (x - y) (y - z)",
            informal_statement="Prove the real absolute-value triangle inequality through an intermediate point.",
        )
    return _inst(
        f"∀ x y z : ℝ, |(x + {k}) - (z + {k})| ≤ |x - y| + |y - z|",
        f"by\n  intro x y z\n  have h : (x + {k}) - (z + {k}) = (x - y) + (y - z) := by\n    ring\n  "
        f"calc\n    |(x + {k}) - (z + {k})| = |(x - y) + (y - z)| := by rw [h]\n    "
        "_ ≤ |x - y| + |y - z| := abs_add_le (x - y) (y - z)",
        informal_statement=f"Prove the real absolute-value triangle inequality after shifting endpoints by {k}.",
    )


def _b_continuous_id_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"Continuous (fun x : ℝ => {k} + x)",
            "by\n  continuity",
            informal_statement=f"Prove that the function adding x to {k} is continuous.",
        )
    return _inst(
        f"Continuous (fun x : ℝ => x + {k})",
        "by\n  continuity",
        informal_statement=f"Prove that the function x ↦ x + {k} is continuous.",
    )


def _b_finset_union_card_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ (A B : Finset (Fin {n})), A.card ≤ (A ∪ B).card",
            "by\n  intro A B\n  exact Finset.card_le_card (by intro x hx; simp [hx])",
            informal_statement=f"Prove that a finite subset of Fin {n} is no larger than its union with another set.",
        )
    return _inst(
        f"∀ (A B : Finset (Fin {n})), (A ∪ B).card ≤ A.card + B.card",
        "by\n  intro A B\n  exact Finset.card_union_le A B",
        informal_statement=f"Prove the cardinality bound for a union of finite subsets of Fin {n}.",
    )


def _b_set_inter_union_distrib_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B C : Set (Fin {n}), (B ∪ C) ∩ A = (B ∩ A) ∪ (C ∩ A)",
            "by\n  intro A B C\n  ext x\n  simp\n  tauto",
            informal_statement=f"Prove the reversed set-intersection distributive law for sets over Fin {n}.",
        )
    return _inst(
        f"∀ A B C : Set (Fin {n}), A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C)",
        "by\n  intro A B C\n  ext x\n  simp\n  tauto",
        informal_statement=f"Prove set intersection distributes over union for sets over Fin {n}.",
    )


def _b_mul_add_distrib_nat_medium(rng: random.Random) -> TemplateInstance:
    a, b, c = rng.randint(1, 30), rng.randint(1, 30), rng.randint(1, 30)
    if rng.choice((False, True)):
        return _inst(
            f"{c} * ({a} + {b}) = {c} * {a} + {c} * {b}",
            "by\n  norm_num",
            informal_statement=f"Prove the concrete distributive identity {c} * ({a} + {b}).",
        )
    return _inst(
        f"({a} + {b}) * {c} = {a} * {c} + {b} * {c}",
        "by\n  norm_num",
        informal_statement=f"Prove the concrete distributive identity ({a} + {b}) * {c}.",
    )


def _b_sq_nonneg_real_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x : ℝ, 0 ≤ (x + {k}) * (x + {k})",
            f"by\n  intro x\n  nlinarith [sq_nonneg (x + {k})]",
            informal_statement=f"Prove that the square of x + {k} is at least zero over the reals.",
        )
    return _inst(
        f"∀ x : ℝ, (x + {k}) * (x + {k}) ≥ 0",
        f"by\n  intro x\n  nlinarith [sq_nonneg (x + {k})]",
        informal_statement=f"Prove that the square of x + {k} is nonnegative over the reals.",
    )


def _b_abs_triangle_int_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℤ, |x + (y + {k})| ≤ |x| + |y + {k}|",
            f"by\n  intro x y\n  exact abs_add_le x (y + {k})",
            informal_statement=f"Prove the integer absolute-value triangle inequality after shifting y by {k}.",
        )
    return _inst(
        f"∀ x y : ℤ, |(x + {k}) + y| ≤ |x + {k}| + |y|",
        f"by\n  intro x y\n  exact abs_add_le (x + {k}) y",
        informal_statement=f"Prove the integer absolute-value triangle inequality after shifting x by {k}.",
    )


def _b_finset_filter_card_le_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(3, 24)
    if rng.choice((False, True)):
        return _inst(
            f"∀ (P : Nat → Prop) [DecidablePred P], "
            f"(Finset.filter P (Finset.range {n})).card ≤ {n}",
            "by\n  intro P inst\n  simpa using Finset.card_filter_le (Finset.range "
            f"{n}) P",
            informal_statement=f"Prove that filtering the finite range below {n} cannot increase it past {n} elements.",
        )
    return _inst(
        f"∀ (P : Nat → Prop) [DecidablePred P], "
        f"(Finset.filter P (Finset.range {n})).card ≤ (Finset.range {n}).card",
        "by\n  intro P inst\n  simpa using Finset.card_filter_le (Finset.range "
        f"{n}) P",
        informal_statement=f"Prove that filtering the finite range below {n} cannot increase its size.",
    )


def _b_sum_range_succ_nat_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 18)
    if rng.choice((False, True)):
        return _inst(
            f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) = "
            f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat))",
            "by\n  exact (Finset.sum_range_succ (fun i : Nat => (i : Nat)) "
            f"{n}).symm",
            informal_statement=f"Prove the finite-sum range step at endpoint {n}.",
        )
    return _inst(
        f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat)) = "
        f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat)",
        "by\n  exact Finset.sum_range_succ (fun i : Nat => (i : Nat)) "
        f"{n}",
        informal_statement=f"Prove the finite-sum range successor identity at endpoint {n}.",
    )


def _b_pow_two_mul_self_nat_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ m : Nat, m * m ^ {k} = m ^ ({k} + 1)",
            "by\n  intro m\n  ring",
            informal_statement=f"Prove that multiplying m by m to the power {k} gives m to the power {k + 1}.",
        )
    return _inst(
        f"∀ m : Nat, m ^ {k} * m = m ^ ({k} + 1)",
        "by\n  intro m\n  ring",
        informal_statement=f"Prove that multiplying m to the power {k} by m gives m to the power {k + 1}.",
    )


def _b_finset_insert_card_easy(rng: random.Random) -> TemplateInstance:
    n = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"(insert {n} (insert {n} (∅ : Finset Nat))).card = 1",
            "by\n  simp",
            informal_statement=f"Prove that inserting {n} twice into the empty finite set still gives one element.",
        )
    return _inst(
        f"(insert {n} (∅ : Finset Nat)).card = 1",
        "by\n  simp",
        informal_statement=f"Prove that inserting {n} into the empty finite set gives one element.",
    )


def _b_logic_and_comm_medium(rng: random.Random) -> TemplateInstance:
    if rng.choice((False, True)):
        return _inst(
            "∀ P Q : Prop, P ∨ Q ↔ Q ∨ P",
            "by\n  intro P Q\n  exact or_comm",
            informal_statement="Prove that disjunction of propositions is commutative.",
        )
    return _inst(
        "∀ P Q : Prop, P ∧ Q ↔ Q ∧ P",
        "by\n  intro P Q\n  exact and_comm",
        informal_statement="Prove that conjunction of propositions is commutative.",
    )


def _b_min_le_left_nat_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b : Nat, min (a + {k}) (b + {k}) ≤ b + {k}",
            f"by\n  intro a b\n  exact min_le_right (a + {k}) (b + {k})",
            informal_statement=f"Prove that the minimum of two numbers shifted by {k} is at most the second one.",
        )
    return _inst(
        f"∀ a b : Nat, min (a + {k}) (b + {k}) ≤ a + {k}",
        f"by\n  intro a b\n  exact min_le_left (a + {k}) (b + {k})",
        informal_statement=f"Prove that the minimum of two numbers shifted by {k} is at most the first shifted number.",
    )


def _b_finset_subset_card_le_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B : Finset (Fin {n}), A.card ≤ (A ∪ B).card",
            "by\n  intro A B\n  exact Finset.card_le_card (by intro x hx; simp [hx])",
            informal_statement=f"Prove that a finite subset of Fin {n} is no larger than its union with another set.",
        )
    return _inst(
        f"∀ A B : Finset (Fin {n}), A ⊆ B → A.card ≤ B.card",
        "by\n  intro A B h\n  exact Finset.card_le_card h",
        informal_statement=f"Prove that subset containment bounds cardinality for finite subsets of Fin {n}.",
    )


def _b_finset_range_card_easy(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 40)
    if rng.choice((False, True)):
        return _inst(
            f"(Finset.range {n}).card + 1 = {n} + 1",
            "by\n  simp",
            informal_statement=f"Prove that the finite range below {n} has cardinality {n} before adding one.",
        )
    return _inst(
        f"(Finset.range {n}).card = {n}",
        "by\n  simp",
        informal_statement=f"Prove that the finite range below {n} has {n} elements.",
    )


def _b_list_append_length_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ xs ys : List Nat, (xs ++ (ys.map (fun n => n + {k}))).length = xs.length + ys.length",
            "by\n  intro xs ys\n  simp",
            informal_statement=(
                f"Prove that appending a list after adding {k} to its entries has the expected length."
            ),
        )
    return _inst(
        f"∀ xs ys : List Nat, ((xs.map (fun n => n + {k})) ++ ys).length = xs.length + ys.length",
        "by\n  intro xs ys\n  simp",
        informal_statement=(
            f"Prove that adding {k} to list entries before appending preserves the append-length formula."
        ),
    )


def _b_set_union_subset_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B : Set (Fin {n}), B ⊆ A ∪ B",
            "by\n  intro A B x hx\n  exact Or.inr hx",
            informal_statement=f"Prove that a set over Fin {n} is contained in another set's union with it.",
        )
    return _inst(
        f"∀ A B : Set (Fin {n}), A ⊆ A ∪ B",
        "by\n  intro A B x hx\n  exact Or.inl hx",
        informal_statement=f"Prove that a set over Fin {n} is contained in its union with another set.",
    )


def _b_set_subset_antisymm_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B : Set (Fin {n}), B ⊆ A → A ⊆ B → A = B",
            "by\n  intro A B hBA hAB\n  exact Set.Subset.antisymm hAB hBA",
            informal_statement=f"Prove set equality over Fin {n} from mutual containments in reverse order.",
        )
    return _inst(
        f"∀ A B : Set (Fin {n}), A ⊆ B → B ⊆ A → A = B",
        "by\n  intro A B hAB hBA\n  exact Set.Subset.antisymm hAB hBA",
        informal_statement=f"Prove set equality over Fin {n} from mutual subset containment.",
    )


# --- New medium builders 40..47.


def _b_real_affine_assoc_medium(rng: random.Random) -> TemplateInstance:
    a, b, c = rng.randint(1, 9), rng.randint(1, 9), rng.randint(1, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x : ℝ, ({a} : ℝ) * x + ({b} + {c}) = (({a} : ℝ) * x + {b}) + {c}",
            "by\n  intro x\n  ring",
            informal_statement=f"Prove the reversed affine identity with coefficients {a}, {b}, and {c}.",
        )
    return _inst(
        f"∀ x : ℝ, (({a} : ℝ) * x + {b}) + {c} = ({a} : ℝ) * x + ({b} + {c})",
        "by\n  intro x\n  ring",
        informal_statement=f"Prove the affine identity with coefficients {a}, {b}, and {c}.",
    )


def _b_int_add_le_add_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 50)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℤ, x ≤ y → {k} + x ≤ {k} + y",
            "by\n  intro x y h\n  omega",
            informal_statement=f"Prove that adding {k} on the left preserves integer order.",
        )
    return _inst(
        f"∀ x y : ℤ, x ≤ y → x + {k} ≤ y + {k}",
        "by\n  intro x y h\n  omega",
        informal_statement=f"Prove that adding {k} to both sides preserves integer order.",
    )


def _b_nat_mul_add_distrib_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b c : Nat, {k} * (c * (a + b)) = {k} * (c * a + c * b)",
            "by\n  intro a b c\n  ring",
            informal_statement=f"Prove distributivity of natural-number multiplication after left-scaling by {k}.",
        )
    return _inst(
        f"∀ a b c : Nat, ((a + b) * c) * {k} = (a * c + b * c) * {k}",
        "by\n  intro a b c\n  ring",
        informal_statement=f"Prove distributivity of natural-number multiplication after scaling by {k}.",
    )


def _b_set_subset_trans_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B C : Set (Fin {n}), B ⊆ C → A ⊆ B → A ⊆ C",
            "by\n  intro A B C hBC hAB x hx\n  exact hBC (hAB hx)",
            informal_statement=f"Prove subset transitivity for sets over Fin {n} with premises reversed.",
        )
    return _inst(
        f"∀ A B C : Set (Fin {n}), A ⊆ B → B ⊆ C → A ⊆ C",
        "by\n  intro A B C hAB hBC x hx\n  exact hBC (hAB hx)",
        informal_statement=f"Prove transitivity of subset containment for sets over Fin {n}.",
    )


def _b_function_comp_assoc_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ f g h : Fin {n} → Fin {n}, ∀ x : Fin {n}, (f ∘ (g ∘ h)) x = ((f ∘ g) ∘ h) x",
            "by\n  intro f g h x\n  rfl",
            informal_statement=f"Prove the reversed associativity identity for function composition on Fin {n}.",
        )
    return _inst(
        f"∀ f g h : Fin {n} → Fin {n}, ∀ x : Fin {n}, ((f ∘ g) ∘ h) x = (f ∘ (g ∘ h)) x",
        "by\n  intro f g h x\n  rfl",
        informal_statement=f"Prove associativity of function composition on Fin {n}.",
    )


def _b_finset_mem_range_succ_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, n ∈ Finset.range (n + {k} + 1)",
            "by\n  intro n\n  simp",
            informal_statement=f"Prove that n belongs to the finite range ending after n plus {k}.",
        )
    return _inst(
        f"∀ n : Nat, n + {k} ∈ Finset.range (n + {k} + 1)",
        "by\n  intro n\n  simp",
        informal_statement=f"Prove that n + {k} belongs to the finite range ending just after it.",
    )


def _b_logic_demorgan_or_medium(rng: random.Random) -> TemplateInstance:
    if rng.choice((False, True)):
        return _inst(
            "∀ P Q : Prop, ¬(Q ∨ P) ↔ ¬P ∧ ¬Q",
            "by\n  intro P Q\n  tauto",
            informal_statement="Prove De Morgan's law for a disjunction written in reverse order.",
        )
    return _inst(
        "∀ P Q : Prop, ¬(P ∨ Q) ↔ ¬P ∧ ¬Q",
        "by\n  intro P Q\n  tauto",
        informal_statement="Prove De Morgan's law for a disjunction of propositions.",
    )


def _b_real_abs_nonneg_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x : ℝ, 0 ≤ |{k} + x|",
            f"by\n  intro x\n  exact abs_nonneg ({k} + x)",
            informal_statement=f"Prove that the absolute value of {k} + x is nonnegative.",
        )
    return _inst(
        f"∀ x : ℝ, 0 ≤ |x + {k}|",
        f"by\n  intro x\n  exact abs_nonneg (x + {k})",
        informal_statement=f"Prove that the absolute value of x + {k} is nonnegative.",
    )


# --- New hard builders 48..71.


def _b_real_cubic_expand_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℝ, (x + (y + {k})) ^ 3 = "
            f"x ^ 3 + 3 * x ^ 2 * (y + {k}) + 3 * x * (y + {k}) ^ 2 + (y + {k}) ^ 3",
            "by\n  intro x y\n  ring",
            informal_statement=f"Prove the cubic expansion after shifting y by {k}.",
        )
    return _inst(
        f"∀ x y : ℝ, ((x + {k}) + y) ^ 3 = "
        f"(x + {k}) ^ 3 + 3 * (x + {k}) ^ 2 * y + 3 * (x + {k}) * y ^ 2 + y ^ 3",
        "by\n  intro x y\n  ring",
        informal_statement=f"Prove the cubic expansion after shifting x by {k}.",
    )


def _b_int_square_sub_square_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 20)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b : ℤ, ((a + {k}) + b) ^ 2 - ((a + {k}) - b) ^ 2 = b * (4 * (a + {k}))",
            "by\n  intro a b\n  ring",
            informal_statement=f"Prove the reversed difference-of-squares product after shifting a by {k}.",
        )
    return _inst(
        f"∀ a b : ℤ, ((a + {k}) + b) ^ 2 - ((a + {k}) - b) ^ 2 = 4 * (a + {k}) * b",
        "by\n  intro a b\n  ring",
        informal_statement=f"Prove the difference-of-squares identity after shifting a by {k}.",
    )


def _b_nat_square_expand_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 20)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b : Nat, (b + (a + {k})) ^ 2 = b ^ 2 + 2 * b * (a + {k}) + (a + {k}) ^ 2",
            "by\n  intro a b\n  ring",
            informal_statement="Prove the natural-number square expansion after putting the shifted term second.",
        )
    return _inst(
        f"∀ a b : Nat, ((a + {k}) + b) ^ 2 = (a + {k}) ^ 2 + 2 * (a + {k}) * b + b ^ 2",
        "by\n  intro a b\n  ring",
        informal_statement=f"Prove the natural-number square expansion after shifting a by {k}.",
    )


def _b_real_two_mul_le_squares_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℝ, 2 * x * (y + {k}) ≤ x * x + (y + {k}) * (y + {k})",
            f"by\n  intro x y\n  nlinarith [sq_nonneg (x - (y + {k}))]",
            informal_statement=f"Prove the quadratic inequality after shifting y by {k}.",
        )
    return _inst(
        f"∀ x y : ℝ, 2 * (x + {k}) * y ≤ (x + {k}) * (x + {k}) + y * y",
        f"by\n  intro x y\n  nlinarith [sq_nonneg ((x + {k}) - y)]",
        informal_statement=f"Prove the quadratic inequality after shifting x by {k}.",
    )


def _b_real_sum_sq_nonneg_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y z : ℝ, 0 ≤ x * x + (y + {k}) * (y + {k}) + z * z",
            f"by\n  intro x y z\n  nlinarith [sq_nonneg x, sq_nonneg (y + {k}), sq_nonneg z]",
            informal_statement=f"Prove that the displayed sum of squares with y shifted by {k} is nonnegative.",
        )
    return _inst(
        f"∀ x y z : ℝ, 0 ≤ (x + {k}) * (x + {k}) + y * y + z * z",
        f"by\n  intro x y z\n  nlinarith [sq_nonneg (x + {k}), sq_nonneg y, sq_nonneg z]",
        informal_statement=f"Prove that the displayed sum of squares with x shifted by {k} is nonnegative.",
    )


def _b_real_sq_sub_nonneg_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℝ, 0 ≤ (x + {k} - y) ^ 2",
            f"by\n  intro x y\n  nlinarith [sq_nonneg (x + {k} - y)]",
            informal_statement=f"Prove that the square of x plus {k} minus y is nonnegative.",
        )
    return _inst(
        f"∀ x y : ℝ, 0 ≤ (x - y + {k}) ^ 2",
        f"by\n  intro x y\n  nlinarith [sq_nonneg (x - y + {k})]",
        informal_statement=f"Prove that the square of x minus y plus {k} is nonnegative.",
    )


def _b_set_union_inter_distrib_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B C : Set (Fin {n}), (B ∩ C) ∪ A = (B ∪ A) ∩ (C ∪ A)",
            "by\n  intro A B C\n  ext x\n  simp\n  tauto",
            informal_statement=f"Prove reversed union-over-intersection distributivity for sets over Fin {n}.",
        )
    return _inst(
        f"∀ A B C : Set (Fin {n}), A ∪ (B ∩ C) = (A ∪ B) ∩ (A ∪ C)",
        "by\n  intro A B C\n  ext x\n  simp\n  tauto",
        informal_statement=f"Prove set union distributes over intersection for sets over Fin {n}.",
    )


def _b_set_diff_union_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B C : Set (Fin {n}), A \\ (B ∩ C) = (A \\ B) ∪ (A \\ C)",
            "by\n  intro A B C\n  ext x\n  simp\n  tauto",
            informal_statement=f"Prove the set-difference identity over an intersection for sets over Fin {n}.",
        )
    return _inst(
        f"∀ A B C : Set (Fin {n}), A \\ (B ∪ C) = (A \\ B) \\ C",
        "by\n  intro A B C\n  ext x\n  simp\n  tauto",
        informal_statement=f"Prove the set-difference identity for sets over Fin {n}.",
    )


def _b_set_subset_preimage_image_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ (f : Fin {n} → Fin {n}) (S : Set (Fin {n})), f '' (f ⁻¹' S) ⊆ S",
            "by\n  intro f S y hy\n  rcases hy with ⟨x, hx, rfl⟩\n  exact hx",
            informal_statement=f"Prove that the image of the preimage of a set over Fin {n} is contained in the set.",
        )
    return _inst(
        f"∀ (f : Fin {n} → Fin {n}) (S : Set (Fin {n})), S ⊆ f ⁻¹' (f '' S)",
        "by\n  intro f S x hx\n  exact ⟨x, hx, rfl⟩",
        informal_statement=f"Prove that a set over Fin {n} is contained in the preimage of its image.",
    )


def _b_logic_curry_hard(rng: random.Random) -> TemplateInstance:
    if rng.choice((False, True)):
        return _inst(
            "∀ P Q R : Prop, (Q → P → R) ↔ (P ∧ Q → R)",
            "by\n  intro P Q R\n  tauto",
            informal_statement="Prove the currying equivalence when the two assumptions are supplied in reverse order.",
        )
    return _inst(
        "∀ P Q R : Prop, (P → Q → R) ↔ (P ∧ Q → R)",
        "by\n  intro P Q R\n  tauto",
        informal_statement="Prove the currying equivalence for propositions.",
    )


def _b_logic_contrapositive_hard(rng: random.Random) -> TemplateInstance:
    if rng.choice((False, True)):
        return _inst(
            "∀ P Q : Prop, (P → Q) → (P ∧ ¬Q → False)",
            "by\n  intro P Q h hpq\n  exact hpq.2 (h hpq.1)",
            informal_statement="Prove that an implication rules out the premise together with the negated conclusion.",
        )
    return _inst(
        "∀ P Q : Prop, (P → Q) → (¬Q → ¬P)",
        "by\n  intro P Q h hnq hp\n  exact hnq (h hp)",
        informal_statement="Prove the displayed contrapositive implication.",
    )


def _b_dvd_sum_sq_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b c : Nat, a ∣ b → a ∣ c → a ∣ b * {k} + c * {k}",
            f"by\n  intro a b c hb hc\n"
            f"  have hb' : a ∣ b * {k} := dvd_mul_of_dvd_left hb {k}\n"
            f"  have hc' : a ∣ c * {k} := dvd_mul_of_dvd_left hc {k}\n"
            f"  exact dvd_add hb' hc'",
            informal_statement=f"Prove divisibility is preserved by a scaled sum using multiplier {k}.",
        )
    return _inst(
        f"∀ a b c : Nat, a ∣ b → a ∣ c → a ∣ b * b * {k} + c * c * {k}",
        f"by\n  intro a b c hb hc\n"
        f"  have hbb : a ∣ b * b * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hb b) {k}\n"
        f"  have hcc : a ∣ c * c * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hc c) {k}\n"
        f"  exact dvd_add hbb hcc",
        informal_statement=f"Prove divisibility is preserved by a sum of squares scaled by {k}.",
    )


def _b_dvd_symmetric_linear_combo_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b c : Nat, a ∣ b → a ∣ b * c * {k}",
            f"by\n  intro a b c hb\n  exact dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hb c) {k}",
            informal_statement=f"Prove divisibility is preserved by one scaled product with multiplier {k}.",
        )
    return _inst(
        f"∀ a b c : Nat, a ∣ b → a ∣ b * c * {k} + c * b * {k}",
        f"by\n  intro a b c hb\n"
        f"  have hbc : a ∣ b * c * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hb c) {k}\n"
        f"  have hcb : a ∣ c * b * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_right hb c) {k}\n"
        f"  exact dvd_add hbc hcb",
        informal_statement=(
            f"Prove divisibility is preserved by the displayed symmetric linear combination scaled by {k}."
        ),
    )


def _b_prime_beyond_shift_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(3, 30)
    if rng.choice((False, True)):
        return _inst(
            "∀ N : Nat, ∃ p : Nat, N ≤ p ∧ Nat.Prime p",
            "by\n  intro N\n  exact Nat.exists_infinite_primes N",
            informal_statement="Prove that beyond every natural-number bound there is a prime number.",
        )
    return _inst(
        f"∀ N : Nat, ∃ p : Nat, N + {k} ≤ p ∧ Nat.Prime p",
        f"by\n  intro N\n  exact Nat.exists_infinite_primes (N + {k})",
        informal_statement=f"Prove that beyond every bound shifted by {k}, there is a prime number.",
    )


def _b_list_reverse_append_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ xs ys : List Nat, ((xs ++ ys).reverse.map (fun n => n + {k})) = "
            f"(ys.reverse.map (fun n => n + {k})) ++ (xs.reverse.map (fun n => n + {k}))",
            "by\n  intro xs ys\n  simp",
            informal_statement=f"Prove that mapping by adding {k} after reversing an append reverses the parts.",
        )
    return _inst(
        f"∀ xs ys : List Nat, ((xs ++ ys).map (fun n => n + {k})).reverse = "
        f"(ys.map (fun n => n + {k})).reverse ++ (xs.map (fun n => n + {k})).reverse",
        "by\n  intro xs ys\n  simp",
        informal_statement=f"Prove that reversing an appended list after adding {k} to entries reverses the parts.",
    )


def _b_list_map_reverse_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 20)
    if rng.choice((False, True)):
        return _inst(
            f"∀ xs : List Nat, xs.reverse.map (fun n => n + {k}) = "
            f"(xs.map (fun n => n + {k})).reverse",
            "by\n  intro xs\n  simp",
            informal_statement=f"Prove the reversed map-reverse identity after adding {k} to entries.",
        )
    return _inst(
        f"∀ xs : List Nat, (xs.map (fun n => n + {k})).reverse = "
        f"xs.reverse.map (fun n => n + {k})",
        "by\n  intro xs\n  simp",
        informal_statement=f"Prove that mapping each list entry by adding {k} commutes with reversing.",
    )


def _b_list_replicate_append_length_hard(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 20)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n m : Nat, (List.replicate n {a}).length + (List.replicate m {a}).length = n + m",
            "by\n  intro n m\n  simp",
            informal_statement=f"Prove the length-sum identity for two lists replicated with value {a}.",
        )
    return _inst(
        f"∀ n m : Nat, (List.replicate n {a} ++ List.replicate m {a}).length = n + m",
        "by\n  intro n m\n  simp",
        informal_statement=f"Prove the append-length identity for lists replicated with value {a}.",
    )


def _b_finset_range_subset_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, Finset.range n ⊆ Finset.range (n + {k})",
            "by\n  intro n x hx\n  simp at hx ⊢\n  omega",
            informal_statement=f"Prove that a finite range is contained in the range shifted upward by {k}.",
        )
    return _inst(
        f"∀ n m : Nat, n ≤ m → Finset.range (n + {k}) ⊆ Finset.range (m + {k})",
        "by\n  intro n m h x hx\n  simp at hx ⊢\n  omega",
        informal_statement=f"Prove finite-range subset containment after shifting both bounds by {k}.",
    )


def _b_finset_card_range_add_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(5, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, (Finset.range (n + {k})).card = n + {k}",
            "by\n  intro n\n  simp",
            informal_statement=f"Prove the finite-range cardinality identity after shifting the endpoint by {k}.",
        )
    return _inst(
        f"∀ n : Nat, (Finset.range n).card + {k} = n + {k}",
        "by\n  intro n\n  simp",
        informal_statement=f"Prove the finite-range cardinality identity after adding {k} to both sides.",
    )


def _b_matrix_transpose_transpose_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 4)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A : Matrix (Fin {n}) (Fin ({n} + 1)) ℤ, A.transpose.transpose = A",
            "by\n  intro A\n  ext i j\n  rfl",
            informal_statement=f"Prove that double transpose restores a {n} by {n + 1} integer matrix.",
        )
    return _inst(
        f"∀ A : Matrix (Fin {n}) (Fin {n}) ℤ, A.transpose.transpose = A",
        "by\n  intro A\n  ext i j\n  rfl",
        informal_statement=f"Prove that transposing a {n} by {n} integer matrix twice gives the original matrix.",
    )


def _b_matrix_add_zero_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 4)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A : Matrix (Fin {n}) (Fin {n}) ℤ, 0 + A = A",
            "by\n  intro A\n  ext i j\n  simp",
            informal_statement=f"Prove that left-adding zero leaves a {n} by {n} integer matrix unchanged.",
        )
    return _inst(
        f"∀ A : Matrix (Fin {n}) (Fin {n}) ℤ, A + 0 = A",
        "by\n  intro A\n  ext i j\n  simp",
        informal_statement=f"Prove that adding zero to a {n} by {n} integer matrix leaves it unchanged.",
    )


def _b_matrix_det_identity_three_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 4)
    if rng.choice((False, True)):
        return _inst(
            f"Matrix.det (1 : Matrix (Fin {n}) (Fin {n}) ℚ) = 1",
            "by\n  simp",
            informal_statement=f"Prove that the {n} by {n} rational identity matrix has determinant one.",
        )
    return _inst(
        f"Matrix.det (1 : Matrix (Fin {n}) (Fin {n}) ℤ) = 1",
        "by\n  simp",
        informal_statement=f"Prove that the {n} by {n} identity matrix has determinant one.",
    )


def _b_continuous_polynomial_hard(rng: random.Random) -> TemplateInstance:
    c = rng.randint(1, 9)
    if rng.choice((False, True)):
        return _inst(
            f"Continuous (fun x : ℝ => (x + {c}) ^ 2 + ({c} : ℝ) * x)",
            "by\n  continuity",
            informal_statement=f"Prove continuity of the polynomial function (x + {c}) squared plus {c} times x.",
        )
    return _inst(
        f"Continuous (fun x : ℝ => (x + {c}) ^ 2 + x)",
        "by\n  continuity",
        informal_statement=f"Prove continuity of the polynomial function (x + {c}) squared plus x.",
    )


def _b_group_inv_mul_hard(rng: random.Random) -> TemplateInstance:
    if rng.choice((False, True)):
        return _inst(
            "∀ (G : Type) [Group G], ∀ a b c : G, (a * b * c)⁻¹ = c⁻¹ * b⁻¹ * a⁻¹",
            "by\n  intro G inst a b c\n  simp [mul_assoc]",
            informal_statement="Prove the inverse-of-product identity for three elements in any group.",
        )
    return _inst(
        "∀ (G : Type) [Group G], ∀ a b : G, (a * b)⁻¹ = b⁻¹ * a⁻¹",
        "by\n  intro G inst a b\n  simp",
        informal_statement="Prove the inverse-of-product identity for two elements in any group.",
    )


def _b_nat_add_zero_induction_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, 0 + (n + {k}) = n + {k}",
            "by\n  intro n\n  induction n with\n  | zero => norm_num\n  | succ n ih => simp [ih]",
            informal_statement=f"Prove by induction that adding zero on the left leaves n + {k} unchanged.",
        )
    return _inst(
        f"∀ n : Nat, n + {k} + 0 = n + {k}",
        "by\n  intro n\n  induction n with\n  | zero => norm_num\n  | succ n ih => simp [ih]",
        informal_statement=f"Prove by induction that adding zero leaves n + {k} unchanged.",
    )


def _b_list_append_nil_induction_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ xs : List Nat, [] ++ (xs.map (fun n => n + {k})) = xs.map (fun n => n + {k})",
            "by\n  intro xs\n  induction xs with\n  | nil => rfl\n  | cons x xs ih => simp [ih]",
            informal_statement=(
                f"Prove by induction that prepending the empty list leaves the list mapped by +{k} unchanged."
            ),
        )
    return _inst(
        f"∀ xs : List Nat, (xs.map (fun n => n + {k})) ++ [] = xs.map (fun n => n + {k})",
        "by\n  intro xs\n  induction xs with\n  | nil => rfl\n  | cons x xs ih => simp [ih]",
        informal_statement=(
            f"Prove by induction that appending the empty list leaves the list mapped by +{k} unchanged."
        ),
    )


def _b_nat_mod_concrete_medium(rng: random.Random) -> TemplateInstance:
    modulus = rng.randint(3, 17)
    value = rng.randint(20, 400)
    if rng.choice((False, True)):
        return _inst(
            f"({value} + {modulus} : Nat) % {modulus} = {value % modulus}",
            "by\n  norm_num",
            informal_statement=f"Prove that adding one modulus leaves {value}'s remainder unchanged modulo {modulus}.",
        )
    return _inst(
        f"({value} : Nat) % {modulus} = {value % modulus}",
        "by\n  norm_num",
        informal_statement=f"Prove the concrete modular-arithmetic identity {value} modulo {modulus}.",
    )


def _b_predicate_exists_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(0, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ P : Nat → Prop, (∀ n : Nat, P n) → ∃ n : Nat, n = {k} ∧ P n",
            f"by\n  intro P h\n  exact ⟨{k}, rfl, h {k}⟩",
            informal_statement=f"Prove that a universally true predicate has witness {k} with the equality first.",
        )
    return _inst(
        f"∀ P : Nat → Prop, (∀ n : Nat, P n) → ∃ n : Nat, P n ∧ n = {k}",
        f"by\n  intro P h\n  exact ⟨{k}, h {k}, rfl⟩",
        informal_statement=f"Prove that a universally true predicate holds at witness {k}.",
    )


def _b_symmetric_relation_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ R : Nat → Nat → Prop, (∀ a b : Nat, R a b → R b a) → "
            f"∀ a b : Nat, R a (b + {k}) → R (b + {k}) a",
            "by\n  intro R h a b hab\n  exact h _ _ hab",
            informal_statement=f"Prove that a symmetric relation reverses after shifting the second argument by {k}.",
        )
    return _inst(
        f"∀ R : Nat → Nat → Prop, (∀ a b : Nat, R a b → R b a) → "
        f"∀ a b : Nat, R (a + {k}) b → R b (a + {k})",
        "by\n  intro R h a b hab\n  exact h _ _ hab",
        informal_statement=f"Prove that a symmetric relation can be reversed after shifting the first argument by {k}.",
    )


def _b_nat_rec_counter_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, Nat.rec {k} (fun _ acc => acc + 1) n = {k} + n",
            "by\n  intro n\n  induction n with\n  | zero => norm_num\n  | succ n ih => "
            "\n      simp [ih]\n      omega",
            informal_statement=f"Prove that a recursive counter starting at {k} returns {k} plus n.",
        )
    return _inst(
        f"∀ n : Nat, Nat.rec {k} (fun _ acc => acc + 1) n = n + {k}",
        "by\n  intro n\n  induction n with\n  | zero => norm_num\n  | succ n ih => "
        "\n      simp [ih]",
        informal_statement=f"Prove that a recursive counter starting at {k} returns n + {k}.",
    )


def _b_set_image_mono_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ (f : Fin {n} → Fin {n}) (A B : Set (Fin {n})), f '' A ⊆ f '' (A ∪ B)",
            "by\n  intro f A B y hy\n  rcases hy with ⟨x, hx, rfl⟩\n  exact ⟨x, Or.inl hx, rfl⟩",
            informal_statement=f"Prove that the image of a set over Fin {n} is contained in the image of its union.",
        )
    return _inst(
        f"∀ (f : Fin {n} → Fin {n}) (A B : Set (Fin {n})), A ⊆ B → f '' A ⊆ f '' B",
        "by\n  intro f A B h y hy\n  rcases hy with ⟨x, hx, rfl⟩\n  exact ⟨x, h hx, rfl⟩",
        informal_statement=f"Prove that image preserves subset containment under a function on Fin {n}.",
    )


def _b_real_quadratic_param_hard(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 7)
    b = rng.randint(1, 7)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x : ℝ, (x + {a}) ^ 2 = x ^ 2 + ({2 * a} : ℝ) * x + ({a * a} : ℝ)",
            "by\n  intro x\n  ring",
            informal_statement=f"Prove the square-form quadratic identity with parameter {a}.",
        )
    return _inst(
        f"∀ x : ℝ, (x + {a}) * (x + {b}) = x ^ 2 + ({a + b} : ℝ) * x + ({a * b} : ℝ)",
        "by\n  intro x\n  ring",
        informal_statement=f"Prove the quadratic identity with parameters {a} and {b}.",
    )


# --- Extreme builders 80..84.


def _b_real_four_point_abs_triangle_extreme(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            "∀ w x y z : ℝ, |w - z| ≤ |w - x| + |x - y| + |y - z|",
            "by\n  intro w x y z\n"
            "  have hyz : w - z = (w - y) + (y - z) := by\n"
            "    ring\n"
            "  have hxy : w - y = (w - x) + (x - y) := by\n"
            "    ring\n"
            "  calc\n"
            "    |w - z| = |(w - y) + (y - z)| := by rw [hyz]\n"
            "    _ ≤ |w - y| + |y - z| := abs_add_le (w - y) (y - z)\n"
            "    _ = |(w - x) + (x - y)| + |y - z| := by rw [hxy]\n"
            "    _ ≤ (|w - x| + |x - y|) + |y - z| := by\n"
            "      nlinarith [abs_add_le (w - x) (x - y)]\n"
            "    _ = |w - x| + |x - y| + |y - z| := by ring",
            informal_statement="Prove the four-point absolute-value triangle inequality.",
        )
    return _inst(
        f"∀ w x y z : ℝ, |(w + {k}) - (z + {k})| ≤ "
        f"|(w + {k}) - (x + {k})| + |(x + {k}) - (y + {k})| + |(y + {k}) - (z + {k})|",
        "by\n  intro w x y z\n"
        f"  have hyz : (w + {k}) - (z + {k}) = ((w + {k}) - (y + {k})) + ((y + {k}) - (z + {k})) := by\n"
        "    ring\n"
        f"  have hxy : (w + {k}) - (y + {k}) = ((w + {k}) - (x + {k})) + ((x + {k}) - (y + {k})) := by\n"
        "    ring\n"
        "  calc\n"
        f"    |(w + {k}) - (z + {k})| = "
        f"|((w + {k}) - (y + {k})) + ((y + {k}) - (z + {k}))| := by rw [hyz]\n"
        f"    _ ≤ |(w + {k}) - (y + {k})| + |(y + {k}) - (z + {k})| := "
        f"abs_add_le ((w + {k}) - (y + {k})) ((y + {k}) - (z + {k}))\n"
        f"    _ = |((w + {k}) - (x + {k})) + ((x + {k}) - (y + {k}))| + "
        f"|(y + {k}) - (z + {k})| := by rw [hxy]\n"
        f"    _ ≤ (|(w + {k}) - (x + {k})| + |(x + {k}) - (y + {k})|) + "
        f"|(y + {k}) - (z + {k})| := by\n"
        f"      nlinarith [abs_add_le ((w + {k}) - (x + {k})) ((x + {k}) - (y + {k}))]\n"
        f"    _ = |(w + {k}) - (x + {k})| + |(x + {k}) - (y + {k})| + "
        f"|(y + {k}) - (z + {k})| := by ring",
        informal_statement=f"Prove the four-point absolute-value triangle inequality after shifting all points by {k}.",
    )


def _b_dvd_three_square_sum_extreme(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ a b c d : Nat, a ∣ b → a ∣ c → a ∣ d → "
            f"a ∣ b * b * {k} + c * c * {k} + d * {k}",
            "by\n  intro a b c d hb hc hd\n"
            f"  have hbb : a ∣ b * b * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hb b) {k}\n"
            f"  have hcc : a ∣ c * c * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hc c) {k}\n"
            f"  have hdd : a ∣ d * {k} := dvd_mul_of_dvd_left hd {k}\n"
            "  exact dvd_add (dvd_add hbb hcc) hdd",
            informal_statement=f"Prove divisibility is preserved by two scaled squares and one scaled term using {k}.",
        )
    return _inst(
        f"∀ a b c d : Nat, a ∣ b → a ∣ c → a ∣ d → "
        f"a ∣ b * b * {k} + c * c * {k} + d * d * {k}",
        "by\n  intro a b c d hb hc hd\n"
        f"  have hbb : a ∣ b * b * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hb b) {k}\n"
        f"  have hcc : a ∣ c * c * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hc c) {k}\n"
        f"  have hdd : a ∣ d * d * {k} := dvd_mul_of_dvd_left (dvd_mul_of_dvd_left hd d) {k}\n"
        "  exact dvd_add (dvd_add hbb hcc) hdd",
        informal_statement=f"Prove divisibility is preserved by a three-square sum scaled by {k}.",
    )


def _b_set_image_subset_chain_extreme(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ (f : Fin {n} → Fin {n}) (A B C : Set (Fin {n})), "
            f"A ⊆ B → B ⊆ C → f '' (A ∪ B) ⊆ f '' C",
            "by\n  intro f A B C hAB hBC y hy\n"
            "  rcases hy with ⟨x, hx, rfl⟩\n"
            "  rcases hx with hxA | hxB\n"
            "  · exact ⟨x, hBC (hAB hxA), rfl⟩\n"
            "  · exact ⟨x, hBC hxB, rfl⟩",
            informal_statement=f"Prove that image preserves a union inside a two-step subset chain on Fin {n}.",
        )
    return _inst(
        f"∀ (f : Fin {n} → Fin {n}) (A B C : Set (Fin {n})), A ⊆ B → B ⊆ C → f '' A ⊆ f '' C",
        "by\n  intro f A B C hAB hBC y hy\n"
        "  rcases hy with ⟨x, hxA, rfl⟩\n"
        "  exact ⟨x, hBC (hAB hxA), rfl⟩",
        informal_statement=f"Prove that image preserves a two-step subset chain under a function on Fin {n}.",
    )


def _b_list_map_reverse_append_extreme(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 20)
    if rng.choice((False, True)):
        return _inst(
            f"∀ xs ys : List Nat, ((xs ++ ys).reverse.map (fun n => n + {k})) = "
            f"(ys.reverse.map (fun n => n + {k})) ++ (xs.reverse.map (fun n => n + {k}))",
            "by\n  intro xs ys\n  simp",
            informal_statement=f"Prove the map-after-reverse append identity after adding {k} to every list entry.",
        )
    return _inst(
        f"∀ xs ys : List Nat, ((xs ++ ys).map (fun n => n + {k})).reverse = "
        f"(ys.map (fun n => n + {k})).reverse ++ (xs.map (fun n => n + {k})).reverse",
        f"by\n  intro xs ys\n"
        f"  calc\n"
        f"    ((xs ++ ys).map (fun n => n + {k})).reverse = "
        f"((xs.map (fun n => n + {k})) ++ (ys.map (fun n => n + {k}))).reverse := by\n"
        f"      simp\n"
        f"    _ = (ys.map (fun n => n + {k})).reverse ++ "
        f"(xs.map (fun n => n + {k})).reverse := by\n"
        f"      simp",
        informal_statement=f"Prove the map-reverse-append identity after adding {k} to every list entry.",
    )


def _b_finset_sum_range_two_steps_extreme(rng: random.Random) -> TemplateInstance:
    n = rng.randint(3, 12)
    if rng.choice((False, True)):
        return _inst(
            f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) + ({n} + 1 : Nat) = "
            f"(∑ i ∈ Finset.range ({n} + 2), (i : Nat))",
            f"by\n  calc\n"
            f"    (∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) + ({n} + 1 : Nat) = "
            f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat)) + ({n} + 1 : Nat) := by\n"
            f"      rw [Finset.sum_range_succ (fun i : Nat => (i : Nat)) {n}]\n"
            f"    _ = (∑ i ∈ Finset.range ({n} + 2), (i : Nat)) := by\n"
            f"      exact (Finset.sum_range_succ (fun i : Nat => (i : Nat)) ({n} + 1)).symm",
            informal_statement=f"Prove the reversed two-step finite-sum range identity starting at endpoint {n}.",
        )
    return _inst(
        f"(∑ i ∈ Finset.range ({n} + 2), (i : Nat)) = "
        f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) + ({n} + 1 : Nat)",
        f"by\n  calc\n"
        f"    (∑ i ∈ Finset.range ({n} + 2), (i : Nat)) = "
        f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat)) + ({n} + 1 : Nat) := by\n"
        f"      exact Finset.sum_range_succ (fun i : Nat => (i : Nat)) ({n} + 1)\n"
        f"    _ = ((∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat)) + ({n} + 1 : Nat) := by\n"
        f"      rw [Finset.sum_range_succ (fun i : Nat => (i : Nat)) {n}]\n"
        f"    _ = (∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) + ({n} + 1 : Nat) := by\n"
        f"      ring",
        informal_statement=f"Prove the two-step finite-sum range identity starting at endpoint {n}.",
    )


# --- New appended families 85..92. Keep previous indices stable.


def _b_nat_sub_self_easy(rng: random.Random) -> TemplateInstance:
    n = rng.randint(1, 500)
    if rng.choice((False, True)):
        return _inst(
            f"({n} : Nat) + {n} - {n} = {n}",
            "by\n  norm_num",
            informal_statement=f"Prove that {n} plus itself minus {n} returns {n}.",
        )
    return _inst(
        f"({n} : Nat) - {n} = 0",
        "by\n  norm_num",
        informal_statement=f"Prove that {n} minus itself is zero.",
    )


def _b_bool_or_easy(rng: random.Random) -> TemplateInstance:
    left = rng.choice((True, False))
    right = rng.choice((True, False))
    result = left or right
    l_txt = str(left).lower()
    r_txt = str(right).lower()
    out_txt = str(result).lower()
    return _inst(
        f"({l_txt} || {r_txt}) = {out_txt}",
        "by\n  rfl",
        informal_statement=f"Prove the Boolean identity {l_txt} OR {r_txt} = {out_txt}.",
    )


def _b_list_cons_length_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 80)
    if rng.choice((False, True)):
        return _inst(
            f"∀ xs : List Nat, (xs ++ [{k}]).length = xs.length + 1",
            "by\n  intro xs\n  simp",
            informal_statement=f"Prove that appending {k} to a list increases its length by one.",
        )
    return _inst(
        f"∀ xs : List Nat, ({k} :: xs).length = xs.length + 1",
        "by\n  intro xs\n  simp",
        informal_statement=f"Prove that prepending {k} to a list increases its length by one.",
    )


def _b_even_shift_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    offset = 2 * k
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, Even ({offset} + 2 * n)",
            f"by\n  intro n\n  use n + {k}\n  ring",
            informal_statement=f"Prove that every number of the form {offset} plus two times n is even.",
        )
    return _inst(
        f"∀ n : Nat, Even (2 * n + {offset})",
        f"by\n  intro n\n  use n + {k}\n  ring",
        informal_statement=f"Prove that every number of the form two times n plus {offset} is even.",
    )


def _b_finset_insert_membership_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 40)
    if rng.choice((False, True)):
        return _inst(
            f"∀ n : Nat, n ∈ Finset.range (n + {k} + 1)",
            "by\n  intro n\n  simp",
            informal_statement=f"Prove that n belongs to the finite range ending after n plus {k}.",
        )
    return _inst(
        f"∀ n : Nat, n ∈ insert n (Finset.range (n + {k} + 1))",
        "by\n  intro n\n  simp",
        informal_statement=f"Prove that n belongs after inserting it into the finite range shifted by {k}.",
    )


def _b_set_union_comm_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ A B : Set (Fin {n}), A ∩ B = B ∩ A",
            "by\n  intro A B\n  ext x\n  simp [and_comm]",
            informal_statement=f"Prove that intersection of sets over Fin {n} is commutative.",
        )
    return _inst(
        f"∀ A B : Set (Fin {n}), A ∪ B = B ∪ A",
        "by\n  intro A B\n  ext x\n  simp [or_comm]",
        informal_statement=f"Prove that union of sets over Fin {n} is commutative.",
    )


def _b_real_shifted_square_lower_bound_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x : ℝ, 0 ≤ (x + {k}) ^ 2",
            f"by\n  intro x\n  nlinarith [sq_nonneg (x + {k})]",
            informal_statement=f"Prove that (x + {k}) squared is nonnegative.",
        )
    return _inst(
        f"∀ x : ℝ, ({k} : ℝ) ≤ (x + {k}) ^ 2 + ({k} : ℝ)",
        f"by\n  intro x\n  nlinarith [sq_nonneg (x + {k})]",
        informal_statement=f"Prove the lower bound from the nonnegativity of (x + {k}) squared.",
    )


def _b_set_image_union_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ (f : Fin {n} → Fin {n}) (A B : Set (Fin {n})), f '' (A ∩ B) ⊆ f '' A ∩ f '' B",
            "by\n  intro f A B y hy\n  rcases hy with ⟨x, hx, rfl⟩\n  exact ⟨⟨x, hx.1, rfl⟩, ⟨x, hx.2, rfl⟩⟩",
            informal_statement=f"Prove the image-intersection containment for functions on Fin {n}.",
        )
    return _inst(
        f"∀ (f : Fin {n} → Fin {n}) (A B : Set (Fin {n})), f '' (A ∪ B) = f '' A ∪ f '' B",
        "by\n  intro f A B\n  ext y\n  constructor\n"
        "  · intro hy\n    rcases hy with ⟨x, hx, rfl⟩\n"
        "    rcases hx with hx | hx\n"
        "    · exact Or.inl ⟨x, hx, rfl⟩\n"
        "    · exact Or.inr ⟨x, hx, rfl⟩\n"
        "  · intro hy\n    rcases hy with ⟨x, hx, rfl⟩ | ⟨x, hx, rfl⟩\n"
        "    · exact ⟨x, Or.inl hx, rfl⟩\n"
        "    · exact ⟨x, Or.inr hx, rfl⟩",
        informal_statement=f"Prove that image distributes over union for functions on Fin {n}.",
    )


# --- New appended families 93..99. Keep previous indices stable.


def _b_real_midpoint_identity_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℝ, ((x + y) / 2 - x) + ({k} : ℝ) = (y - x) / 2 + ({k} : ℝ)",
            "by\n  intro x y\n  ring",
            informal_statement=f"Prove the midpoint displacement identity after adding {k} to both sides.",
        )
    return _inst(
        f"∀ x y : ℝ, ((x + y) / 2 - y) + ({k} : ℝ) = (x - y) / 2 + ({k} : ℝ)",
        "by\n  intro x y\n  ring",
        informal_statement=f"Prove the reversed midpoint displacement identity after adding {k} to both sides.",
    )


def _b_real_finite_average_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℝ, ((x + y) / 2) * 2 + ({k} : ℝ) = x + y + ({k} : ℝ)",
            "by\n  intro x y\n  ring",
            informal_statement=f"Prove that doubling a two-term average recovers the total, shifted by {k}.",
        )
    return _inst(
        f"∀ x y z : ℝ, ((x + y + z) / 3) * 3 + ({k} : ℝ) = x + y + z + ({k} : ℝ)",
        "by\n  intro x y z\n  ring",
        informal_statement=f"Prove that tripling a three-term average recovers the total, shifted by {k}.",
    )


def _b_real_difference_quotient_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            "∀ x h : ℝ, h ≠ 0 → ((x + h) ^ 2 - x ^ 2) / h = 2 * x + h",
            "by\n  intro x h hh\n  field_simp [hh]\n  ring",
            informal_statement="Prove the square-function difference quotient at a nonzero step.",
        )
    return _inst(
        f"∀ x h : ℝ, h ≠ 0 → (((x + h + {k}) - (x + {k})) / h) = 1",
        "by\n  intro x h hh\n  field_simp [hh]\n  ring",
        informal_statement=f"Prove the affine difference quotient with intercept {k}.",
    )


def _b_finset_constant_one_sum_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            "∀ n : Nat, (∑ _i ∈ Finset.range n, (1 : Nat)) = n",
            "by\n  intro n\n  simp",
            informal_statement="Prove that summing ones over a finite range returns the range length.",
        )
    return _inst(
        f"∀ n : Nat, (∑ _i ∈ Finset.range (n + {k}), (1 : Nat)) = n + {k}",
        "by\n  intro n\n  simp",
        informal_statement=f"Prove that summing ones over a finite range shifted by {k} returns its length.",
    )


def _b_simple_graph_adjacency_symmetry_hard(rng: random.Random) -> TemplateInstance:
    n = rng.randint(3, 9)
    if rng.choice((False, True)):
        return _inst(
            f"∀ (G : SimpleGraph (Fin {n})) {{u v : Fin {n}}}, G.Adj u v → G.Adj v u",
            "by\n  intro G u v h\n  exact G.symm h",
            informal_statement=f"Prove that adjacency in a simple graph on Fin {n} is symmetric.",
        )
    return _inst(
        f"∀ (G : SimpleGraph (Fin {n})) {{u v w : Fin {n}}}, "
        "G.Adj u v → G.Adj v w → G.Adj v u ∧ G.Adj w v",
        "by\n  intro G u v w huv hvw\n  exact ⟨G.symm huv, G.symm hvw⟩",
        informal_statement=f"Prove two reversed adjacency facts in a simple graph on Fin {n}.",
    )


def _b_linear_diophantine_witness_hard(rng: random.Random) -> TemplateInstance:
    a = rng.randint(2, 9)
    b = rng.randint(2, 9)
    x = rng.randint(3, 12)
    y = rng.randint(1, 8)
    if rng.choice((False, True)):
        rhs = a * x + b * y
        return _inst(
            f"∃ x y : ℤ, ({a} : ℤ) * x + ({b} : ℤ) * y = ({rhs} : ℤ)",
            f"by\n  refine ⟨{x}, {y}, ?_⟩\n  norm_num",
            informal_statement=f"Prove that the integer equation {a}x + {b}y = {rhs} has a witness.",
        )
    rhs = a * (x + y) - b * y
    return _inst(
        f"∃ x y : ℤ, ({a} : ℤ) * x - ({b} : ℤ) * y = ({rhs} : ℤ)",
        f"by\n  refine ⟨{x + y}, {y}, ?_⟩\n  norm_num",
        informal_statement=f"Prove that the integer equation {a}x - {b}y = {rhs} has a witness.",
    )


def _b_real_amgm_square_inequality_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 12)
    if rng.choice((False, True)):
        return _inst(
            f"∀ x y : ℝ, 2 * x * y + ({k} : ℝ) ≤ x ^ 2 + y ^ 2 + ({k} : ℝ)",
            "by\n  intro x y\n  nlinarith [sq_nonneg (x - y)]",
            informal_statement=f"Prove a shifted two-term square inequality with offset {k}.",
        )
    return _inst(
        f"∀ x y : ℝ, 4 * x * y + ({k} : ℝ) ≤ (x + y) ^ 2 + ({k} : ℝ)",
        "by\n  intro x y\n  nlinarith [sq_nonneg (x - y)]",
        informal_statement=f"Prove a shifted square inequality for the sum x plus y with offset {k}.",
    )


_RAW_BUILDERS: tuple[GeneratedTemplate, ...] = (
    GeneratedTemplate("easy", "algebra.basic", "nat_mul_one", _b_nat_mul_one_easy),
    GeneratedTemplate("easy", "algebra.basic", "nat_arithmetic", _b_nat_add_norm_easy),
    GeneratedTemplate("easy", "algebra.order", "nat_order", _b_nat_le_norm_easy),
    GeneratedTemplate("easy", "logic.propositional", "booleans", _b_bool_and_easy),
    GeneratedTemplate("easy", "combinatorics.counting", "list_length", _b_list_len_easy),
    GeneratedTemplate("easy", "combinatorics.counting", "list_reverse_length", _b_list_reverse_len_easy),
    GeneratedTemplate("easy", "analysis.real_basic", "real_arithmetic", _b_real_add_norm_easy),
    GeneratedTemplate("easy", "combinatorics.finite_sets", "finset_range_card", _b_finset_card_easy),
    GeneratedTemplate("medium", "algebra.order", "reflexive_order", _b_forall_le_refl_medium),
    GeneratedTemplate("medium", "combinatorics.counting", "list_reverse_length", _b_list_reverse_length_medium),
    GeneratedTemplate("medium", "algebra.basic", "nat_commutativity", _b_add_comm_nat_medium),
    GeneratedTemplate("medium", "algebra.basic", "nat_associativity", _b_mul_assoc_nat_medium),
    GeneratedTemplate("medium", "algebra.ring", "real_polynomial_identity", _b_sq_expand_real_medium),
    GeneratedTemplate("medium", "logic.propositional", "implication", _b_implication_true_medium),
    GeneratedTemplate("medium", "number_theory.divisibility", "odd_numbers", _b_odd_square_odd_medium),
    GeneratedTemplate("medium", "number_theory.divisibility", "divisibility_trans", _b_dvd_trans_medium),
    GeneratedTemplate("medium", "set_theory.finite_sets", "set_subset", _b_set_inter_subset_medium),
    GeneratedTemplate("medium", "combinatorics.counting", "finset_sum_range", _b_sum_range_medium),
    GeneratedTemplate("medium", "linear_algebra.matrix", "matrix_det_identity", _b_det_unit_medium),
    GeneratedTemplate("medium", "geometry.metric", "real_abs_triangle", _b_metric_triangle_medium),
    GeneratedTemplate("medium", "analysis.continuity", "continuous_identity", _b_continuous_id_medium),
    GeneratedTemplate("hard", "number_theory.primes", "prime_witness", _b_exists_prime_dvd_hard),
    GeneratedTemplate("hard", "number_theory.primes", "infinite_primes", _b_inf_many_primes_hard),
    GeneratedTemplate("hard", "algebra.ring", "rational_square_not_two", _b_rational_square_not_two_hard),
    GeneratedTemplate("hard", "combinatorics.finite_sets", "finset_union_card", _b_finset_union_card_hard),
    GeneratedTemplate("hard", "set_theory.finite_sets", "set_distributivity", _b_set_inter_union_distrib_hard),
    GeneratedTemplate("medium", "algebra.ring", "nat_distributivity_instance", _b_mul_add_distrib_nat_medium),
    GeneratedTemplate("medium", "analysis.real_basic", "real_square_nonneg", _b_sq_nonneg_real_medium),
    GeneratedTemplate("medium", "algebra.order", "integer_abs_triangle", _b_abs_triangle_int_medium),
    GeneratedTemplate("medium", "combinatorics.finite_sets", "finset_filter_card", _b_finset_filter_card_le_medium),
    GeneratedTemplate("medium", "combinatorics.counting", "finset_sum_range", _b_sum_range_succ_nat_medium),
    GeneratedTemplate("hard", "algebra.ring", "nat_power_identity", _b_pow_two_mul_self_nat_hard),
    GeneratedTemplate("easy", "combinatorics.finite_sets", "finset_insert", _b_finset_insert_card_easy),
    GeneratedTemplate("medium", "logic.propositional", "logic_commutativity", _b_logic_and_comm_medium),
    GeneratedTemplate("medium", "algebra.order", "nat_min_order", _b_min_le_left_nat_medium),
    GeneratedTemplate("hard", "combinatorics.finite_sets", "finset_subset_card", _b_finset_subset_card_le_hard),
    GeneratedTemplate("easy", "combinatorics.finite_sets", "finset_range_card", _b_finset_range_card_easy),
    GeneratedTemplate("medium", "combinatorics.counting", "list_append_length", _b_list_append_length_medium),
    GeneratedTemplate("medium", "set_theory.finite_sets", "set_union_subset", _b_set_union_subset_medium),
    GeneratedTemplate("hard", "set_theory.finite_sets", "set_antisymmetry", _b_set_subset_antisymm_hard),
    GeneratedTemplate("medium", "algebra.ring", "real_affine_identity", _b_real_affine_assoc_medium),
    GeneratedTemplate("medium", "algebra.order", "integer_monotonicity", _b_int_add_le_add_medium),
    GeneratedTemplate("medium", "algebra.ring", "nat_distributivity", _b_nat_mul_add_distrib_medium),
    GeneratedTemplate("medium", "set_theory.finite_sets", "set_subset_trans", _b_set_subset_trans_medium),
    GeneratedTemplate("medium", "category_theory.trivial", "function_composition", _b_function_comp_assoc_medium),
    GeneratedTemplate(
        "medium",
        "combinatorics.finite_sets",
        "finset_range_membership",
        _b_finset_mem_range_succ_medium,
    ),
    GeneratedTemplate("medium", "logic.propositional", "demorgan", _b_logic_demorgan_or_medium),
    GeneratedTemplate("medium", "analysis.norm", "absolute_value", _b_real_abs_nonneg_medium),
    GeneratedTemplate("hard", "algebra.ring", "real_cubic_identity", _b_real_cubic_expand_hard),
    GeneratedTemplate("hard", "algebra.ring", "integer_square_identity", _b_int_square_sub_square_hard),
    GeneratedTemplate("hard", "algebra.ring", "nat_square_identity", _b_nat_square_expand_hard),
    GeneratedTemplate("hard", "optimization.inequalities", "quadratic_inequality", _b_real_two_mul_le_squares_hard),
    GeneratedTemplate("hard", "optimization.inequalities", "sum_squares_nonneg", _b_real_sum_sq_nonneg_hard),
    GeneratedTemplate("hard", "optimization.inequalities", "square_difference_nonneg", _b_real_sq_sub_nonneg_hard),
    GeneratedTemplate("hard", "set_theory.finite_sets", "set_union_inter_distrib", _b_set_union_inter_distrib_hard),
    GeneratedTemplate("hard", "set_theory.finite_sets", "set_difference", _b_set_diff_union_hard),
    GeneratedTemplate("hard", "set_theory.finite_sets", "image_preimage", _b_set_subset_preimage_image_hard),
    GeneratedTemplate("hard", "logic.propositional", "logic_curry", _b_logic_curry_hard),
    GeneratedTemplate("hard", "logic.propositional", "contrapositive", _b_logic_contrapositive_hard),
    GeneratedTemplate("hard", "number_theory.divisibility", "divisibility_sum_squares", _b_dvd_sum_sq_hard),
    GeneratedTemplate(
        "hard",
        "number_theory.divisibility",
        "divisibility_linear_combo",
        _b_dvd_symmetric_linear_combo_hard,
    ),
    GeneratedTemplate("hard", "number_theory.primes", "prime_beyond_shift", _b_prime_beyond_shift_hard),
    GeneratedTemplate("hard", "combinatorics.counting", "list_reverse_append", _b_list_reverse_append_hard),
    GeneratedTemplate("hard", "combinatorics.counting", "list_map_reverse", _b_list_map_reverse_hard),
    GeneratedTemplate("hard", "combinatorics.counting", "list_replicate_append", _b_list_replicate_append_length_hard),
    GeneratedTemplate("hard", "combinatorics.finite_sets", "finset_range_subset", _b_finset_range_subset_hard),
    GeneratedTemplate("hard", "combinatorics.finite_sets", "finset_card_range", _b_finset_card_range_add_hard),
    GeneratedTemplate("hard", "linear_algebra.matrix", "matrix_transpose", _b_matrix_transpose_transpose_hard),
    GeneratedTemplate("hard", "linear_algebra.matrix", "matrix_add_zero", _b_matrix_add_zero_hard),
    GeneratedTemplate("hard", "linear_algebra.matrix", "matrix_det_identity", _b_matrix_det_identity_three_hard),
    GeneratedTemplate("hard", "analysis.continuity", "continuous_polynomial", _b_continuous_polynomial_hard),
    GeneratedTemplate("hard", "abstract_algebra.group_laws", "group_inverse", _b_group_inv_mul_hard),
    GeneratedTemplate("medium", "foundations.recursion", "nat_add_zero_induction", _b_nat_add_zero_induction_medium),
    GeneratedTemplate(
        "medium",
        "foundations.recursion",
        "list_append_nil_induction",
        _b_list_append_nil_induction_medium,
    ),
    GeneratedTemplate("medium", "number_theory.mod_arith", "nat_mod_concrete", _b_nat_mod_concrete_medium),
    GeneratedTemplate("medium", "logic.predicates", "predicate_exists", _b_predicate_exists_medium),
    GeneratedTemplate("medium", "graph_theory.discrete", "symmetric_relation", _b_symmetric_relation_medium),
    GeneratedTemplate("hard", "foundations.recursion", "nat_rec_counter", _b_nat_rec_counter_hard),
    GeneratedTemplate("hard", "set_theory.finite_sets", "set_image_mono", _b_set_image_mono_hard),
    GeneratedTemplate("hard", "algebra.polynomial_light", "real_quadratic_param", _b_real_quadratic_param_hard),
    GeneratedTemplate(
        "extreme",
        "geometry.metric",
        "four_point_abs_triangle",
        _b_real_four_point_abs_triangle_extreme,
    ),
    GeneratedTemplate(
        "extreme",
        "number_theory.divisibility",
        "divisibility_three_squares",
        _b_dvd_three_square_sum_extreme,
    ),
    GeneratedTemplate(
        "extreme",
        "set_theory.finite_sets",
        "set_image_subset_chain",
        _b_set_image_subset_chain_extreme,
    ),
    GeneratedTemplate(
        "extreme",
        "combinatorics.counting",
        "list_map_reverse_append",
        _b_list_map_reverse_append_extreme,
    ),
    GeneratedTemplate(
        "extreme",
        "combinatorics.finite_sets",
        "finset_sum_range_two_steps",
        _b_finset_sum_range_two_steps_extreme,
    ),
    GeneratedTemplate("easy", "algebra.basic", "nat_sub_self", _b_nat_sub_self_easy),
    GeneratedTemplate("easy", "logic.propositional", "boolean_or", _b_bool_or_easy),
    GeneratedTemplate("medium", "combinatorics.counting", "list_cons_length", _b_list_cons_length_medium),
    GeneratedTemplate("medium", "number_theory.divisibility", "even_shift", _b_even_shift_medium),
    GeneratedTemplate(
        "medium",
        "combinatorics.finite_sets",
        "finset_insert_membership",
        _b_finset_insert_membership_medium,
    ),
    GeneratedTemplate("hard", "set_theory.finite_sets", "set_union_comm", _b_set_union_comm_hard),
    GeneratedTemplate(
        "hard",
        "optimization.inequalities",
        "real_shifted_square_lower_bound",
        _b_real_shifted_square_lower_bound_hard,
    ),
    GeneratedTemplate("hard", "set_theory.finite_sets", "set_image_union", _b_set_image_union_hard),
    GeneratedTemplate("medium", "geometry.algebraic_light", "midpoint_identity", _b_real_midpoint_identity_medium),
    GeneratedTemplate(
        "medium",
        "probability.expectation_light",
        "finite_average_identity",
        _b_real_finite_average_medium,
    ),
    GeneratedTemplate("hard", "calculus.limits_light", "difference_quotient", _b_real_difference_quotient_hard),
    GeneratedTemplate(
        "medium",
        "analysis.series_light",
        "finite_constant_series",
        _b_finset_constant_one_sum_medium,
    ),
    GeneratedTemplate(
        "hard",
        "graph_theory.discrete",
        "simple_graph_symmetry",
        _b_simple_graph_adjacency_symmetry_hard,
    ),
    GeneratedTemplate(
        "hard",
        "number_theory.mod_arith",
        "linear_diophantine_witness",
        _b_linear_diophantine_witness_hard,
    ),
    GeneratedTemplate(
        "hard",
        "optimization.inequalities",
        "amgm_square_inequality",
        _b_real_amgm_square_inequality_hard,
    ),
)


def _bind_builder(builder_index: int, template: GeneratedTemplate) -> Callable[[random.Random, int], Problem]:
    """Capture builder index so theorem names stay unique per ``(seed, template)``."""

    def _run(rng: random.Random, seed: int) -> Problem:
        name = _theorem_name(seed, builder_index)
        instance = template.build(rng)
        p = _mk_problem(
            seed=seed,
            topic=template.topic,
            family=template.family,
            split=template.split,
            theorem_name=name,
            instance=instance,
        )
        return replace(
            p,
            extra={
                **p.extra,
                "builder_index": builder_index,
                "template_fn": template.build.__name__,
            },
        )

    return _run


# Consensus-critical: append-only ordering; indices appear in ``_theorem_name``.
_BUILDERS: tuple[tuple[Split, Callable[[random.Random, int], Problem]], ...] = tuple(
    (template.split, _bind_builder(i, template)) for i, template in enumerate(_RAW_BUILDERS)
)

_SPLIT_INDICES: dict[str, tuple[int, ...]] = {
    split: tuple(i for i, template in enumerate(_RAW_BUILDERS) if template.split == split) for split in VALID_SPLITS
}


def _problem_for_builder_index(seed: int, builder_index: int, rng: random.Random | None = None) -> Problem:
    """Deterministically materialize one exact builder; used by CI promotion gates."""
    if builder_index < 0 or builder_index >= len(_BUILDERS):
        raise IndexError(builder_index)
    run_rng = rng if rng is not None else random.Random(expand_seed_for_problem_rng(seed))
    _split, factory = _BUILDERS[builder_index]
    return factory(run_rng, seed)


def _source_sha256(obj: Callable[..., Any]) -> str:
    return hashlib.sha256(inspect.getsource(obj).encode("utf-8")).hexdigest()


def _template_source_sha256(template: GeneratedTemplate) -> str:
    return _source_sha256(template.build)


def generated_registry_canonical_dict() -> dict[str, object]:
    """Stable description of template registry (for ``lemma config meta`` and optional pinning)."""
    split_counts = {
        split: sum(1 for template in _RAW_BUILDERS if template.split == split) for split in VALID_SPLITS
    }
    return {
        "kind": "lemma_generated_registry_v2",
        "rng_mix_tag": RNG_MIX_TAG,
        "split_weights": dict(DEFAULT_SPLIT_WEIGHTS),
        "topics": list(TOPICS),
        "builder_count": len(_RAW_BUILDERS),
        "split_counts": split_counts,
        "builder_runtime_source_sha256": _source_sha256(_mk_problem),
        "builders": [
            {
                "index": i,
                "split": template.split,
                "topic": template.topic,
                "family": template.family,
                "informal_statement": GENERATED_FAMILY_STATEMENTS[template.family],
                "fn": template.build.__name__,
                "source_sha256": _template_source_sha256(template),
            }
            for i, template in enumerate(_RAW_BUILDERS)
        ],
    }


def generated_registry_sha256() -> str:
    """SHA-256 of canonical JSON; changes when generated registry behavior changes."""
    canonical = json.dumps(
        generated_registry_canonical_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class GeneratedProblemSource(ProblemSource):
    """Expand ``seed`` into one theorem via deterministic RNG + template registry."""

    def __init__(self, *, legacy_plain_rng: bool = False) -> None:
        """If ``legacy_plain_rng``, use ``random.Random(seed)``; else SHA256-mixed seed."""
        self._legacy_plain_rng = legacy_plain_rng

    def all_problems(self) -> list[Problem]:
        """No finite enumeration (countably infinite id space)."""
        return []

    def sample(self, seed: int, split: str | None = None) -> Problem:
        rng_seed = int(seed) if self._legacy_plain_rng else expand_seed_for_problem_rng(int(seed))
        rng = random.Random(rng_seed)

        if split is not None:
            split_key = split.strip().lower()
            if split_key not in _SPLIT_INDICES:
                raise ValueError(f"unknown generated problem split {split!r}")
            indices = _SPLIT_INDICES[split_key]
            return _problem_for_builder_index(int(seed), indices[rng.randrange(len(indices))], rng)

        pick = rng.randrange(sum(DEFAULT_SPLIT_WEIGHTS.values()))
        offset = 0
        for split_key in VALID_SPLITS:
            offset += DEFAULT_SPLIT_WEIGHTS[split_key]
            if pick < offset:
                indices = _SPLIT_INDICES[split_key]
                return _problem_for_builder_index(int(seed), indices[rng.randrange(len(indices))], rng)
        raise AssertionError("unreachable split selection")

    def get(self, problem_id: str) -> Problem:
        """Parse ``gen/<int>`` ids (same expansion as ``sample``)."""
        if not problem_id.startswith("gen/"):
            raise KeyError(problem_id)
        tail = problem_id.removeprefix("gen/").strip()
        try:
            seed = int(tail, 10)
        except ValueError as e:
            raise KeyError(problem_id) from e
        return self.sample(seed)
