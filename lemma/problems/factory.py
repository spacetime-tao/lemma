"""Construct the active :class:`~lemma.problems.base.ProblemSource` from settings."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lemma.problems.base import Problem, ProblemSource
from lemma.problems.generated import GeneratedProblemSource
from lemma.problems.minif2f import MiniF2FSource

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def get_problem_source(settings: LemmaSettings) -> ProblemSource:
    """Return generated (default) or frozen JSON catalog backend."""
    mode = (settings.problem_source or "generated").strip().lower()
    if mode == "frozen":
        return MiniF2FSource(settings.minif2f_catalog_path)
    if mode != "generated":
        raise ValueError(f"Unknown LEMMA_PROBLEM_SOURCE={settings.problem_source!r}")
    return GeneratedProblemSource()


def resolve_problem(settings: LemmaSettings, problem_id: str) -> Problem:
    """Resolve ``gen/<int>`` via generation; otherwise load frozen catalog."""
    if problem_id.startswith("gen/"):
        return GeneratedProblemSource().get(problem_id)
    return MiniF2FSource(settings.minif2f_catalog_path).get(problem_id)
