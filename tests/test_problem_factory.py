"""Problem source factory for WTA v1."""

import pytest
from lemma.common.config import LemmaSettings
from lemma.problems.factory import get_problem_source, resolve_problem
from lemma.problems.known_theorems import KnownTheoremsSource
from pydantic import ValidationError


def test_known_theorems_default() -> None:
    src = get_problem_source(LemmaSettings(_env_file=None))

    assert isinstance(src, KnownTheoremsSource)


def test_config_rejects_removed_source_names() -> None:
    for source in ("generated", "hybrid", "frozen"):
        with pytest.raises(ValidationError):
            LemmaSettings(_env_file=None, problem_source=source)


def test_resolve_known_theorem_id() -> None:
    p = resolve_problem(LemmaSettings(_env_file=None), "known/smoke/nat_two_plus_two_eq_four")

    assert p.id == "known/smoke/nat_two_plus_two_eq_four"
    assert p.extra["source_lane"] == "known_theorems"


def test_resolve_non_known_id_is_not_public_wta_surface() -> None:
    with pytest.raises(KeyError):
        resolve_problem(LemmaSettings(_env_file=None), "gen/42")
