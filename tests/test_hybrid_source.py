"""Hybrid generated + curated problem supply."""

from collections import Counter

import pytest
from lemma.problems.generated import GeneratedProblemSource
from lemma.problems.hybrid import (
    HybridProblemSource,
    curated_catalog_canonical_rows,
    curated_catalog_sha256,
    problem_supply_registry_canonical_dict,
    problem_supply_registry_sha256,
    validate_curated_catalog_rows,
)


def test_curated_catalog_rows_have_dashboard_metadata() -> None:
    rows = curated_catalog_canonical_rows()
    assert len(rows) >= 12
    assert {row["split"] for row in rows} >= {"easy", "medium", "hard", "extreme"}
    assert len({row["topic"] for row in rows}) >= 10
    assert all(row["informal_statement"].startswith("Prove") for row in rows)


def test_curated_catalog_gate_rejects_missing_informal_statement() -> None:
    rows = [dict(row) for row in curated_catalog_canonical_rows()]
    rows[0]["informal_statement"] = ""
    with pytest.raises(ValueError, match="informal_statement"):
        validate_curated_catalog_rows(rows)


def test_curated_catalog_gate_rejects_missing_positive_weight_split() -> None:
    rows = [dict(row) for row in curated_catalog_canonical_rows() if row["split"] != "extreme"]
    with pytest.raises(ValueError, match="missing positive-weight splits: extreme"):
        validate_curated_catalog_rows(rows)


def test_hybrid_sampling_is_deterministic_and_uses_both_lanes() -> None:
    src = HybridProblemSource()
    first = [src.sample(seed) for seed in range(500)]
    second = [src.sample(seed) for seed in range(500)]

    assert [(p.id, p.type_expr) for p in first] == [(p.id, p.type_expr) for p in second]
    assert {p.extra["source_lane"] for p in first} == {"generated", "catalog"}
    assert {p.split for p in first} >= {"easy", "medium", "hard", "extreme"}
    assert all(p.extra.get("informal_statement") for p in first)


def test_hybrid_picks_split_before_lane() -> None:
    src = HybridProblemSource()
    draws = [src.sample(seed) for seed in range(2_000)]
    splits = Counter(p.split for p in draws)
    lanes = Counter(p.extra["source_lane"] for p in draws)

    assert 60 <= splits["extreme"] <= 140
    assert 1_100 <= lanes["generated"] <= 1_300
    assert 700 <= lanes["catalog"] <= 900


def test_hybrid_explicit_extreme_split_can_use_both_lanes() -> None:
    src = HybridProblemSource()
    draws = [src.sample(seed, split="extreme") for seed in range(200)]

    assert {p.split for p in draws} == {"extreme"}
    assert {p.extra["source_lane"] for p in draws} == {"generated", "catalog"}


def test_hybrid_weights_can_select_generated_only() -> None:
    src = HybridProblemSource(generated_weight=1, catalog_weight=0)
    assert {src.sample(seed).extra["source_lane"] for seed in range(20)} == {"generated"}


def test_hybrid_source_improves_topic_family_breadth_over_generated_baseline() -> None:
    hybrid = [HybridProblemSource().sample(seed) for seed in range(500)]
    generated = [GeneratedProblemSource().sample(seed) for seed in range(500)]

    assert len({p.extra["topic"] for p in hybrid}) > len({p.extra["topic"] for p in generated})
    assert len({p.extra["family"] for p in hybrid}) > len({p.extra["family"] for p in generated})


def test_problem_supply_registry_hash_covers_weights_and_catalog() -> None:
    canonical = problem_supply_registry_canonical_dict()
    assert canonical["weights"] == {"generated": 60, "catalog": 40}
    assert canonical["split_weights"] == {"easy": 10, "medium": 35, "hard": 50, "extreme": 5}
    assert canonical["curated_catalog_sha256"] == curated_catalog_sha256()
    assert len(problem_supply_registry_sha256()) == 64
    assert problem_supply_registry_sha256(generated_weight=100, catalog_weight=0) != problem_supply_registry_sha256()
