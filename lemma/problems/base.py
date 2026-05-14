"""Problem catalog abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

# Solution.lean bridges Challenge ↔ Submission with `exact Submission.<theorem_name>`.
# The bridge theorem must use a name **different** from `theorem_name`, otherwise after
# `import Submission` Lean reports "`theorem_name` has already been declared".
SOLUTION_BRIDGE_THEOREM = "LemmaSubmissionBridge"


@dataclass(frozen=True)
class Problem:
    """One formal theorem round."""

    id: str
    theorem_name: str
    type_expr: str
    split: str
    lean_toolchain: str
    mathlib_rev: str
    imports: tuple[str, ...] = ("Mathlib",)
    extra: dict[str, Any] = field(default_factory=dict)

    def challenge_source(self) -> str:
        """Trusted Challenge.lean body (single theorem, sorry)."""
        cf = self.extra.get("challenge_full")
        if isinstance(cf, str) and cf.strip():
            imps = "\n".join(f"import {m}" for m in self.imports)
            body = cf.strip()
            if self.imports and not body.lstrip().startswith("import "):
                return f"{imps}\n\n{body}\n"
            return body + "\n"

        imps = "\n".join(f"import {m}" for m in self.imports)
        return f"""{imps}

theorem {self.theorem_name} : {self.type_expr} := by
  sorry
"""

    def solution_source(self) -> str:
        """Trusted Solution.lean: bridge to Submission."""
        sf = self.extra.get("solution_full")
        if isinstance(sf, str) and sf.strip():
            return sf.strip() + "\n"

        imps = "\n".join(f"import {m}" for m in self.imports)
        return f"""{imps}
import Submission

theorem {SOLUTION_BRIDGE_THEOREM} : {self.type_expr} := by
  exact Submission.{self.theorem_name}
"""

    def submission_stub(self) -> str:
        """Initial Submission.lean skeleton (miner replaces proof)."""
        st = self.extra.get("submission_stub")
        if isinstance(st, str) and st.strip():
            return st.strip() + "\n"

        imps = "\n".join(f"import {m}" for m in self.imports)
        return f"""{imps}

namespace Submission

theorem {self.theorem_name} : {self.type_expr} := by
  sorry

end Submission
"""


class ProblemSource(ABC):
    """Pluggable theorem source (miniF2F today, lean-eval later)."""

    @abstractmethod
    def all_problems(self) -> list[Problem]:
        """Return full catalog."""

    @abstractmethod
    def sample(self, seed: int, split: str | None = None) -> Problem:
        """Deterministic pick for metronome rounds."""

    @abstractmethod
    def get(self, problem_id: str) -> Problem:
        """Return one problem by stable id."""
