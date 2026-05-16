"""miniF2F-backed problem source from frozen JSON."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from lemma.problems.base import Problem, ProblemSource


def _load_frozen_bytes() -> bytes:
    here = Path(__file__).resolve().parent / "minif2f_frozen.json"
    return here.read_bytes()


def _row_to_problem(row: dict[str, Any]) -> Problem:
    if "imports" in row:
        raw = row["imports"]
        if isinstance(raw, str):
            imports = (raw,)
        else:
            imports = tuple(raw)
    else:
        imports = ("Mathlib",)
    return Problem(
        id=str(row["id"]),
        theorem_name=str(row["theorem_name"]),
        type_expr=str(row["type_expr"]),
        split=str(row.get("split", "unknown")),
        lean_toolchain=str(row["lean_toolchain"]),
        mathlib_rev=str(row["mathlib_rev"]),
        imports=tuple(imports),
        extra={k: v for k, v in row.items() if k not in _FROZEN_KEYS},
    )


_FROZEN_KEYS = frozenset(
    {
        "id",
        "theorem_name",
        "type_expr",
        "split",
        "lean_toolchain",
        "mathlib_rev",
        "imports",
    }
)


class MiniF2FSource(ProblemSource):
    """Load problems from ``minif2f_frozen.json`` (ship a seed subset; regenerate via script)."""

    def __init__(self, path: Path | None = None) -> None:
        raw = path.read_bytes() if path is not None else _load_frozen_bytes()
        rows = json.loads(raw.decode("utf-8"))
        if not isinstance(rows, list):
            raise ValueError("minif2f_frozen.json must be a JSON array")
        self._problems: list[Problem] = [_row_to_problem(r) for r in rows]

    def all_problems(self) -> list[Problem]:
        return list(self._problems)

    def sample(self, seed: int, split: str | None = None) -> Problem:
        rng = random.Random(seed)
        pool = [p for p in self._problems if split is None or p.split == split]
        if not pool:
            pool = self._problems
        return rng.choice(pool)

    def get(self, problem_id: str) -> Problem:
        for p in self._problems:
            if p.id == problem_id:
                return p
        raise KeyError(problem_id)
