"""Construct and resolve the known-theorem problem source."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.problems.base import Problem, ProblemSource
from lemma.problems.known_theorems import KnownTheoremsSource

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def get_problem_source(settings: LemmaSettings) -> ProblemSource:
    if settings.problem_source != "known_theorems":
        raise ValueError("Lemma currently only supports LEMMA_PROBLEM_SOURCE=known_theorems")
    return KnownTheoremsSource(
        manifest_path=settings.known_theorems_manifest_path,
        ledger_path=settings.solved_ledger_path,
    )


def resolve_problem(settings: LemmaSettings, problem_id: str) -> Problem:
    if not problem_id.startswith("known/"):
        raise KeyError(problem_id)
    return KnownTheoremsSource(
        manifest_path=settings.known_theorems_manifest_path,
        ledger_path=settings.solved_ledger_path,
    ).get(problem_id)
