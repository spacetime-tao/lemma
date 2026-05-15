"""Cadence source that combines curated and generated tasks."""

from __future__ import annotations

from lemma.ledger import solved_target_ids
from lemma.problems.base import Problem, ProblemSource
from lemma.problems.generated import GeneratedCadenceSource
from lemma.problems.known_theorems import KnownTheoremsSource


class HybridCadenceSource(ProblemSource):
    """Curated manifest first, then deterministic generated cadence tasks."""

    def __init__(self, curated: KnownTheoremsSource, generated: GeneratedCadenceSource | None = None) -> None:
        self._curated = curated
        self._generated = generated or GeneratedCadenceSource()
        self._problems = [*self._curated.all_problems(), *self._generated.all_problems()]

    def all_problems(self) -> list[Problem]:
        return list(self._problems)

    def sample(self, seed: int, split: str | None = None) -> Problem:
        hashes = {problem.id: problem.theorem_statement_sha256() for problem in self._problems}
        solved = solved_target_ids(self._curated.ledger_path, hashes)
        for problem in self._problems:
            if problem.id not in solved:
                return problem
        raise ValueError("all cadence targets are solved")

    def get(self, problem_id: str) -> Problem:
        for problem in self._problems:
            if problem.id == problem_id:
                return problem
        raise KeyError(problem_id)

    def target_window(self) -> tuple[Problem | None, Problem | None, Problem | None]:
        hashes = {problem.id: problem.theorem_statement_sha256() for problem in self._problems}
        solved = solved_target_ids(self._curated.ledger_path, hashes)
        active_index = next((idx for idx, problem in enumerate(self._problems) if problem.id not in solved), None)
        if active_index is None:
            previous = self._problems[-1] if self._problems else None
            return previous, None, None
        previous = self._problems[active_index - 1] if active_index > 0 else None
        current = self._problems[active_index]
        next_problem = self._problems[active_index + 1] if active_index + 1 < len(self._problems) else None
        return previous, current, next_problem
