"""Problem source factory for known-theorem targets."""

import pytest
from lemma.common.config import LemmaSettings
from lemma.problems.factory import get_problem_source, resolve_problem
from lemma.problems.hybrid import HybridCadenceSource
from lemma.problems.known_theorems import KnownTheoremsSource
from pydantic import ValidationError


def test_hybrid_cadence_default() -> None:
    src = get_problem_source(LemmaSettings(_env_file=None))

    assert isinstance(src, HybridCadenceSource)
    assert len(src.all_problems()) == 100
    assert src.all_problems()[0].id.startswith("gen/easy/")


def test_known_theorems_source_is_still_available() -> None:
    src = get_problem_source(LemmaSettings(_env_file=None, problem_source="known_theorems"))

    assert isinstance(src, KnownTheoremsSource)


def test_config_rejects_removed_source_names() -> None:
    for source in ("generated", "frozen"):
        with pytest.raises(ValidationError):
            LemmaSettings(_env_file=None, problem_source=source)


def test_resolve_known_theorem_id() -> None:
    p = resolve_problem(LemmaSettings(_env_file=None), "known/smoke/nat_two_plus_two_eq_four")

    assert p.id == "known/smoke/nat_two_plus_two_eq_four"
    assert p.extra["source_lane"] == "known_theorems"


def test_resolve_generated_cadence_id() -> None:
    p = resolve_problem(LemmaSettings(_env_file=None), "gen/easy/0")

    assert p.id == "gen/easy/0"
    assert p.extra["source_lane"] == "generated"
