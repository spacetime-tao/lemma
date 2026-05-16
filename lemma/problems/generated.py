"""Small deterministic cadence theorem supply."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable

from lemma.cadence import SPLIT_WEIGHTS
from lemma.problems.base import Problem, ProblemSource

Builder = Callable[[random.Random, int], tuple[str, str, str]]

VALID_SPLITS: tuple[str, ...] = ("easy", "medium", "hard", "extreme")
GENERATED_SUPPLY_COUNT = sum(SPLIT_WEIGHTS.values())


def generated_registry_sha256() -> str:
    payload = {
        "kind": "lemma_generated_registry_v3",
        "split_weights": SPLIT_WEIGHTS,
        "builders": {split: [builder.__name__ for builder in _BUILDERS[split]] for split in VALID_SPLITS},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


class GeneratedCadenceSource(ProblemSource):
    """Deterministic 100-window generated supply with easy/medium/hard/extreme splits."""

    def all_problems(self) -> list[Problem]:
        return [self.sample(seed) for seed in range(GENERATED_SUPPLY_COUNT)]

    def sample(self, seed: int, split: str | None = None) -> Problem:
        seed_i = int(seed)
        split_key = _split_for_seed(seed_i) if split is None else _clean_split(split)
        rng = random.Random(_rng_seed(seed_i, split_key))
        builders = _BUILDERS[split_key]
        builder = builders[rng.randrange(len(builders))]
        title, theorem_name, type_expr = builder(rng, seed_i)
        return _mk_problem(seed=seed_i, split=split_key, title=title, theorem_name=theorem_name, type_expr=type_expr)

    def get(self, problem_id: str) -> Problem:
        parts = problem_id.split("/")
        if len(parts) == 3 and parts[0] == "gen":
            return self.sample(int(parts[2]), split=parts[1])
        if len(parts) == 2 and parts[0] == "gen":
            return self.sample(int(parts[1]))
        raise KeyError(problem_id)


def _clean_split(split: str) -> str:
    key = split.strip().lower()
    if key not in SPLIT_WEIGHTS:
        raise ValueError(f"unknown generated problem split: {split!r}")
    return key


def _split_for_seed(seed: int) -> str:
    slot = int(seed) % GENERATED_SUPPLY_COUNT
    cursor = 0
    for split, count in SPLIT_WEIGHTS.items():
        cursor += int(count)
        if slot < cursor:
            return split
    raise AssertionError("unreachable split")


def _rng_seed(seed: int, split: str) -> int:
    digest = hashlib.sha256(f"lemma-generated-v3:{split}:{int(seed)}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def _theorem_name(split: str, seed: int, family: str) -> str:
    digest = hashlib.sha256(f"{split}:{family}:{int(seed)}".encode()).hexdigest()[:12]
    return f"generated_{split}_{family}_{digest}"


def _mk_problem(*, seed: int, split: str, title: str, theorem_name: str, type_expr: str) -> Problem:
    challenge = f"""import Mathlib

namespace Submission

theorem {theorem_name} : {type_expr} := by
  sorry

end Submission
"""
    return Problem(
        id=f"gen/{split}/{seed}",
        theorem_name=theorem_name,
        type_expr=type_expr,
        split=split,
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        imports=("Mathlib",),
        extra={
            "source_lane": "generated",
            "title": title,
            "difficulty": split,
            "topic": _topic_for_split(split),
            "seed": seed,
            "order": 10_000 + (seed % GENERATED_SUPPLY_COUNT),
            "source_url": f"https://lemmasub.net/examples/cadence/{seed % GENERATED_SUPPLY_COUNT:04d}/",
            "challenge_full": challenge,
            "submission_stub": challenge,
        },
    )


def _topic_for_split(split: str) -> str:
    return {
        "easy": "arithmetic.basic",
        "medium": "logic.and_lists",
        "hard": "algebra.order",
        "extreme": "algebra.identities",
    }[split]


def _b_easy_nat(rng: random.Random, seed: int) -> tuple[str, str, str]:
    a = rng.randint(1, 60)
    b = rng.randint(1, 60)
    return (
        f"Natural arithmetic {a} + {b}",
        _theorem_name("easy", seed, "nat_add"),
        f"({a} : Nat) + {b} = {a + b}",
    )


def _b_easy_bool(rng: random.Random, seed: int) -> tuple[str, str, str]:
    left = rng.choice(("true", "false"))
    right = rng.choice(("true", "false"))
    result = str(left == "true" and right == "true").lower()
    return (
        f"Boolean conjunction {left} and {right}",
        _theorem_name("easy", seed, "bool_and"),
        f"({left} && {right}) = {result}",
    )


def _b_medium_list(rng: random.Random, seed: int) -> tuple[str, str, str]:
    shift = rng.randint(1, 20)
    return (
        f"List map preserves length by {shift}",
        _theorem_name("medium", seed, "list_map_length"),
        f"∀ xs : List Nat, (xs.map (fun n => n + {shift})).length = xs.length",
    )


def _b_medium_logic(_rng: random.Random, seed: int) -> tuple[str, str, str]:
    return (
        "Conjunction implication flip",
        _theorem_name("medium", seed, "and_comm"),
        "∀ p q : Prop, p ∧ q → q ∧ p",
    )


def _b_hard_nat_order(rng: random.Random, seed: int) -> tuple[str, str, str]:
    k = rng.randint(2, 40)
    return (
        f"Natural order shifted by {k}",
        _theorem_name("hard", seed, "nat_order"),
        f"∀ n : Nat, n ≤ n + {k}",
    )


def _b_hard_real_square(_rng: random.Random, seed: int) -> tuple[str, str, str]:
    return (
        "Real square nonnegative",
        _theorem_name("hard", seed, "real_square_nonneg"),
        "∀ x : ℝ, 0 ≤ x ^ 2",
    )


def _b_extreme_quadratic(rng: random.Random, seed: int) -> tuple[str, str, str]:
    k = rng.randint(1, 12)
    return (
        f"Shifted square lower bound {k}",
        _theorem_name("extreme", seed, "shifted_square"),
        f"∀ x : ℝ, ({k} : ℝ) ≤ x ^ 2 + {k}",
    )


def _b_extreme_four_point(_rng: random.Random, seed: int) -> tuple[str, str, str]:
    return (
        "Four point absolute-value triangle",
        _theorem_name("extreme", seed, "four_point_abs"),
        "∀ a b c d : ℝ, |a - d| ≤ |a - b| + |b - c| + |c - d|",
    )


_BUILDERS: dict[str, tuple[Builder, ...]] = {
    "easy": (_b_easy_nat, _b_easy_bool),
    "medium": (_b_medium_list, _b_medium_logic),
    "hard": (_b_hard_nat_order, _b_hard_real_square),
    "extreme": (_b_extreme_quadratic, _b_extreme_four_point),
}
