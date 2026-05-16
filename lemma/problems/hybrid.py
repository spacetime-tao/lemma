"""Cadence source that combines curated and generated tasks."""

from __future__ import annotations

from lemma.problems.base import Problem, ProblemSource
from lemma.problems.generated import GENERATED_SUPPLY_COUNT, GeneratedCadenceSource
from lemma.problems.known_theorems import KnownTheoremsSource


class HybridCadenceSource(ProblemSource):
    """Deterministic generated cadence tasks, with curated targets still resolvable by id."""

    def __init__(self, curated: KnownTheoremsSource, generated: GeneratedCadenceSource | None = None) -> None:
        self._curated = curated
        self._generated = generated or GeneratedCadenceSource()
        self._problems = self._generated.all_problems()

    def all_problems(self) -> list[Problem]:
        return list(self._problems)

    def sample(self, seed: int, split: str | None = None) -> Problem:
        return self._generated.sample(seed=seed, split=split)

    def get(self, problem_id: str) -> Problem:
        for problem in self._problems:
            if problem.id == problem_id:
                return problem
        if problem_id.startswith("gen/"):
            return self._generated.get(problem_id)
        if problem_id.startswith("known/"):
            return self._curated.get(problem_id)
        raise KeyError(problem_id)

    def target_window(self) -> tuple[Problem | None, Problem | None, Problem | None]:
        current = self._generated.sample(0)
        previous = self._generated.sample(GENERATED_SUPPLY_COUNT - 1)
        next_problem = self._generated.sample(1)
        return previous, current, next_problem
