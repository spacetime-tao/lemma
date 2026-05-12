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

Split = Literal["easy", "medium", "hard"]

VALID_SPLITS: tuple[Split, ...] = ("easy", "medium", "hard")
DEFAULT_SPLIT_WEIGHTS: dict[Split, int] = {"easy": 10, "medium": 35, "hard": 55}
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


TemplateBuilder = Callable[[random.Random], TemplateInstance]


@dataclass(frozen=True)
class GeneratedTemplate:
    split: Split
    topic: str
    family: str
    build: TemplateBuilder


def expand_seed_for_problem_rng(seed: int) -> int:
    """Deterministic 64-bit stir for ``random.Random``."""
    digest = hashlib.sha256(f"{RNG_MIX_TAG}|{seed}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _theorem_name(seed: int, builder_index: int) -> str:
    """Stable Lean identifier; separate builders must not collide for the same seed."""
    mix = (seed & 0xFFFFFFFF) ^ (builder_index * 1_000_003)
    return "t_" + format(abs(mix) & ((1 << 48) - 1), "x")


def _inst(type_expr: str, proof: str) -> TemplateInstance:
    return TemplateInstance(type_expr=type_expr.strip(), witness_proof=proof.strip())


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


def _b_true_easy(rng: random.Random) -> TemplateInstance:
    return _inst("True", "by\n  trivial")


def _b_nat_add_norm_easy(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 200)
    b = rng.randint(1, 200)
    return _inst(f"({a} : Nat) + {b} = {a + b}", "by\n  norm_num")


def _b_nat_le_norm_easy(rng: random.Random) -> TemplateInstance:
    lo = rng.randint(0, 50)
    hi = lo + rng.randint(1, 80)
    return _inst(f"({lo} : Nat) ≤ {hi}", "by\n  norm_num")


def _b_bool_and_easy(rng: random.Random) -> TemplateInstance:
    return _inst("(true && false) = false", "by\n  rfl")


def _b_list_len_easy(rng: random.Random) -> TemplateInstance:
    return _inst("([1, 2, 3] : List Nat).length = 3", "by\n  rfl")


def _b_list_reverse_len_easy(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 40)
    b = rng.randint(1, 40)
    c = rng.randint(1, 40)
    return _inst(f"([{a}, {b}, {c}] : List Nat).reverse.length = 3", "by\n  simp")


def _b_real_add_norm_easy(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 20)
    b = rng.randint(1, 20)
    return _inst(f"({a} : ℝ) + ({b} : ℝ) = ({a + b} : ℝ)", "by\n  norm_num")


def _b_finset_card_easy(rng: random.Random) -> TemplateInstance:
    return _inst("(Finset.range 1).card = 1", "by\n  simp")


def _b_forall_le_refl_medium(rng: random.Random) -> TemplateInstance:
    return _inst("∀ n : Nat, n ≤ n", "by\n  intro n\n  exact le_rfl")


def _b_list_reverse_length_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ xs : List Nat, xs.reverse.length = xs.length",
        "by\n  intro xs\n  simp",
    )


def _b_add_comm_nat_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b : Nat, a + b = b + a",
        "by\n  intro a b\n  exact Nat.add_comm a b",
    )


def _b_mul_assoc_nat_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b c : Nat, a * (b * c) = (a * b) * c",
        "by\n  intro a b c\n  exact (Nat.mul_assoc a b c).symm",
    )


def _b_sq_expand_real_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x y : ℝ, (x + y) ^ 2 = x ^ 2 + 2 * x * y + y ^ 2",
        "by\n  intro x y\n  ring",
    )


def _b_implication_true_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ P : Prop, True → P ∨ True",
        "by\n  intro P _\n  exact Or.inr True.intro",
    )


def _b_odd_square_odd_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ n : Nat, Odd (2 * n + 1)",
        "by\n  intro n\n  use n\n  ring",
    )


def _b_dvd_trans_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b c : Nat, a ∣ b → b ∣ c → a ∣ c",
        "by\n  intro a b c hab hbc\n  exact dvd_trans hab hbc",
    )


def _b_set_inter_subset_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B : Set Nat, A ∩ B ⊆ A",
        "by\n  intro A B x hx\n  exact hx.1",
    )


def _b_sum_range_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 15)
    return _inst(
        f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat) = "
        f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat))",
        "by\n  simp",
    )


def _b_exists_prime_dvd_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∃ p : Nat, Nat.Prime p ∧ p ∣ 2",
        "by\n  refine ⟨2, Nat.prime_two, ?_⟩\n  exact dvd_rfl",
    )


def _b_inf_many_primes_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ N : Nat, ∃ p : Nat, N ≤ p ∧ Nat.Prime p",
        "by\n  intro N\n  exact Nat.exists_infinite_primes N",
    )


def _b_sqrt2_irrational_hard(rng: random.Random) -> TemplateInstance:
    return _inst("Irrational (Real.sqrt 2)", "by\n  exact irrational_sqrt_two")


def _b_det_unit_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "Matrix.det (1 : Matrix (Fin 2) (Fin 2) ℤ) = 1",
        "by\n  simp",
    )


def _b_metric_triangle_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x y z : ℝ, |x - z| ≤ |x - y| + |y - z|",
        "by\n  intro x y z\n  simpa [sub_eq_add_neg, add_assoc, add_comm, add_left_comm] "
        "using abs_add (x - y) (y - z)",
    )


def _b_continuous_id_medium(rng: random.Random) -> TemplateInstance:
    return _inst("Continuous (fun x : ℝ => x)", "by\n  simpa using continuous_id")


def _b_finset_union_card_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ (A B : Finset Nat), (A ∪ B).card ≤ A.card + B.card",
        "by\n  intro A B\n  exact Finset.card_union_le A B",
    )


def _b_set_inter_union_distrib_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B C : Set Nat, A ∩ (B ∪ C) = (A ∩ B) ∪ (A ∩ C)",
        "by\n  intro A B C\n  ext x\n  simp\n  tauto",
    )


def _b_mul_add_distrib_nat_medium(rng: random.Random) -> TemplateInstance:
    a, b, c = rng.randint(1, 30), rng.randint(1, 30), rng.randint(1, 30)
    return _inst(f"({a} + {b}) * {c} = {a} * {c} + {b} * {c}", "by\n  norm_num")


def _b_sq_nonneg_real_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x : ℝ, x * x ≥ 0",
        "by\n  intro x\n  nlinarith [sq_nonneg x]",
    )


def _b_abs_triangle_int_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x y : ℤ, |x + y| ≤ |x| + |y|",
        "by\n  intro x y\n  exact abs_add x y",
    )


def _b_finset_filter_card_le_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(3, 24)
    return _inst(
        f"∀ (P : Nat → Prop) [DecidablePred P], "
        f"(Finset.filter P (Finset.range {n})).card ≤ (Finset.range {n}).card",
        "by\n  intro P inst\n  simpa using Finset.card_filter_le (Finset.range "
        f"{n}) P",
    )


def _b_sum_range_succ_nat_medium(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 18)
    return _inst(
        f"(∑ i ∈ Finset.range ({n} + 1), (i : Nat)) = "
        f"(∑ i ∈ Finset.range {n}, (i : Nat)) + ({n} : Nat)",
        "by\n  simp",
    )


def _b_pow_two_mul_self_nat_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(2, 9)
    return _inst(
        f"∀ m : Nat, m ^ {k} * m = m ^ ({k} + 1)",
        "by\n  intro m\n  ring",
    )


def _b_finset_insert_card_easy(rng: random.Random) -> TemplateInstance:
    n = rng.randint(1, 40)
    return _inst(f"(insert {n} (∅ : Finset Nat)).card = 1", "by\n  simp")


def _b_logic_and_comm_medium(rng: random.Random) -> TemplateInstance:
    return _inst("∀ P Q : Prop, P ∧ Q ↔ Q ∧ P", "by\n  intro P Q\n  exact and_comm")


def _b_min_le_left_nat_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b : Nat, min a b ≤ a",
        "by\n  intro a b\n  exact min_le_left a b",
    )


def _b_finset_subset_card_le_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B : Finset Nat, A ⊆ B → A.card ≤ B.card",
        "by\n  intro A B h\n  exact Finset.card_le_card h",
    )


def _b_finset_range_card_easy(rng: random.Random) -> TemplateInstance:
    n = rng.randint(2, 40)
    return _inst(f"(Finset.range {n}).card = {n}", "by\n  simp")


def _b_list_append_length_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ xs ys : List Nat, (xs ++ ys).length = xs.length + ys.length",
        "by\n  intro xs ys\n  simp",
    )


def _b_set_union_subset_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B : Set Nat, A ⊆ A ∪ B",
        "by\n  intro A B x hx\n  exact Or.inl hx",
    )


def _b_set_subset_antisymm_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B : Set Nat, A ⊆ B → B ⊆ A → A = B",
        "by\n  intro A B hAB hBA\n  exact Set.Subset.antisymm hAB hBA",
    )


# --- New medium builders 40..47.


def _b_real_affine_assoc_medium(rng: random.Random) -> TemplateInstance:
    a, b, c = rng.randint(1, 9), rng.randint(1, 9), rng.randint(1, 9)
    return _inst(
        f"∀ x : ℝ, (({a} : ℝ) * x + {b}) + {c} = ({a} : ℝ) * x + ({b} + {c})",
        "by\n  intro x\n  ring",
    )


def _b_int_add_le_add_medium(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 50)
    return _inst(
        f"∀ x y : ℤ, x ≤ y → x + {k} ≤ y + {k}",
        "by\n  intro x y h\n  omega",
    )


def _b_nat_mul_add_distrib_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b c : Nat, (a + b) * c = a * c + b * c",
        "by\n  intro a b c\n  ring",
    )


def _b_set_subset_trans_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B C : Set Nat, A ⊆ B → B ⊆ C → A ⊆ C",
        "by\n  intro A B C hAB hBC x hx\n  exact hBC (hAB hx)",
    )


def _b_function_comp_assoc_medium(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ f g h : Nat → Nat, ∀ x : Nat, ((f ∘ g) ∘ h) x = (f ∘ (g ∘ h)) x",
        "by\n  intro f g h x\n  rfl",
    )


def _b_finset_mem_range_succ_medium(rng: random.Random) -> TemplateInstance:
    return _inst("∀ n : Nat, n ∈ Finset.range (n + 1)", "by\n  intro n\n  simp")


def _b_logic_demorgan_or_medium(rng: random.Random) -> TemplateInstance:
    return _inst("∀ P Q : Prop, ¬(P ∨ Q) ↔ ¬P ∧ ¬Q", "by\n  intro P Q\n  tauto")


def _b_real_abs_nonneg_medium(rng: random.Random) -> TemplateInstance:
    return _inst("∀ x : ℝ, 0 ≤ |x|", "by\n  intro x\n  exact abs_nonneg x")


# --- New hard builders 48..71.


def _b_real_cubic_expand_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x y : ℝ, (x + y) ^ 3 = x ^ 3 + 3 * x ^ 2 * y + 3 * x * y ^ 2 + y ^ 3",
        "by\n  intro x y\n  ring",
    )


def _b_int_square_sub_square_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b : ℤ, (a + b) ^ 2 - (a - b) ^ 2 = 4 * a * b",
        "by\n  intro a b\n  ring",
    )


def _b_nat_square_expand_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b : Nat, (a + b) ^ 2 = a ^ 2 + 2 * a * b + b ^ 2",
        "by\n  intro a b\n  ring",
    )


def _b_real_two_mul_le_squares_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x y : ℝ, 2 * x * y ≤ x * x + y * y",
        "by\n  intro x y\n  nlinarith [sq_nonneg (x - y)]",
    )


def _b_real_sum_sq_nonneg_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x y z : ℝ, 0 ≤ x * x + y * y + z * z",
        "by\n  intro x y z\n  nlinarith [sq_nonneg x, sq_nonneg y, sq_nonneg z]",
    )


def _b_real_sq_sub_nonneg_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ x y : ℝ, 0 ≤ (x - y) ^ 2",
        "by\n  intro x y\n  nlinarith [sq_nonneg (x - y)]",
    )


def _b_set_union_inter_distrib_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B C : Set Nat, A ∪ (B ∩ C) = (A ∪ B) ∩ (A ∪ C)",
        "by\n  intro A B C\n  ext x\n  simp\n  tauto",
    )


def _b_set_diff_union_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A B C : Set Nat, A \\ (B ∪ C) = (A \\ B) \\ C",
        "by\n  intro A B C\n  ext x\n  simp\n  tauto",
    )


def _b_set_subset_preimage_image_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ (f : Nat → Nat) (S : Set Nat), S ⊆ f ⁻¹' (f '' S)",
        "by\n  intro f S x hx\n  exact ⟨x, hx, rfl⟩",
    )


def _b_logic_curry_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ P Q R : Prop, (P → Q → R) ↔ (P ∧ Q → R)",
        "by\n  intro P Q R\n  tauto",
    )


def _b_logic_contrapositive_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ P Q : Prop, (P → Q) → (¬Q → ¬P)",
        "by\n  intro P Q h hnq hp\n  exact hnq (h hp)",
    )


def _b_dvd_sum_sq_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b c : Nat, a ∣ b → a ∣ c → a ∣ b * b + c * c",
        "by\n  intro a b c hb hc\n  exact dvd_add (dvd_mul_of_dvd_left hb b) "
        "(dvd_mul_of_dvd_left hc c)",
    )


def _b_dvd_symmetric_linear_combo_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ a b c : Nat, a ∣ b → a ∣ b * c + c * b",
        "by\n  intro a b c hb\n  exact dvd_add (dvd_mul_of_dvd_left hb c) "
        "(dvd_mul_of_dvd_right hb c)",
    )


def _b_prime_beyond_shift_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(3, 30)
    return _inst(
        f"∀ N : Nat, ∃ p : Nat, N + {k} ≤ p ∧ Nat.Prime p",
        f"by\n  intro N\n  exact Nat.exists_infinite_primes (N + {k})",
    )


def _b_list_reverse_append_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ xs ys : List Nat, (xs ++ ys).reverse = ys.reverse ++ xs.reverse",
        "by\n  intro xs ys\n  simp",
    )


def _b_list_map_reverse_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(1, 20)
    return _inst(
        f"∀ xs : List Nat, (xs.map (fun n => n + {k})).reverse = "
        f"xs.reverse.map (fun n => n + {k})",
        "by\n  intro xs\n  simp",
    )


def _b_list_replicate_append_length_hard(rng: random.Random) -> TemplateInstance:
    a = rng.randint(1, 20)
    return _inst(
        f"∀ n m : Nat, (List.replicate n {a} ++ List.replicate m {a}).length = n + m",
        "by\n  intro n m\n  simp",
    )


def _b_finset_range_subset_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ n m : Nat, n ≤ m → Finset.range n ⊆ Finset.range m",
        "by\n  intro n m h x hx\n  simp at hx ⊢\n  omega",
    )


def _b_finset_card_range_add_hard(rng: random.Random) -> TemplateInstance:
    k = rng.randint(5, 40)
    return _inst(
        f"∀ n : Nat, (Finset.range n).card + {k} = n + {k}",
        "by\n  intro n\n  simp",
    )


def _b_matrix_transpose_transpose_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A : Matrix (Fin 2) (Fin 2) ℤ, A.transpose.transpose = A",
        "by\n  intro A\n  ext i j\n  rfl",
    )


def _b_matrix_add_zero_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ A : Matrix (Fin 2) (Fin 2) ℤ, A + 0 = A",
        "by\n  intro A\n  ext i j\n  simp",
    )


def _b_matrix_det_identity_three_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "Matrix.det (1 : Matrix (Fin 3) (Fin 3) ℤ) = 1",
        "by\n  simp",
    )


def _b_continuous_polynomial_hard(rng: random.Random) -> TemplateInstance:
    c = rng.randint(1, 9)
    return _inst(
        f"Continuous (fun x : ℝ => (x + {c}) ^ 2 + x)",
        "by\n  continuity",
    )


def _b_group_inv_mul_hard(rng: random.Random) -> TemplateInstance:
    return _inst(
        "∀ (G : Type) [Group G], ∀ a b : G, (a * b)⁻¹ = b⁻¹ * a⁻¹",
        "by\n  intro G inst a b\n  simp",
    )


_RAW_BUILDERS: tuple[GeneratedTemplate, ...] = (
    GeneratedTemplate("easy", "logic.propositional", "truth", _b_true_easy),
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
    GeneratedTemplate("hard", "number_theory.primes", "sqrt_two_irrational", _b_sqrt2_irrational_hard),
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
    """Stable description of template registry (for ``lemma meta`` and optional pinning)."""
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
