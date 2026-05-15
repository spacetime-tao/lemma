"""Construct and resolve the known-theorem problem source."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.problems.base import Problem, ProblemSource
from lemma.problems.hybrid import HybridCadenceSource
from lemma.problems.known_theorems import KnownTheoremsSource

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def get_problem_source(settings: LemmaSettings) -> ProblemSource:
    curated = KnownTheoremsSource(
        manifest_path=settings.known_theorems_manifest_path,
        ledger_path=settings.solved_ledger_path,
    )
    if settings.problem_source == "known_theorems":
        return curated
    if settings.problem_source == "hybrid":
        return HybridCadenceSource(curated)
    raise ValueError("Lemma supports LEMMA_PROBLEM_SOURCE=hybrid or known_theorems")


def resolve_problem(settings: LemmaSettings, problem_id: str) -> Problem:
    if not problem_id.startswith(("known/", "gen/")):
        raise KeyError(problem_id)
    return get_problem_source(settings).get(problem_id)
