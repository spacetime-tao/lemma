"""Materialize a per-problem Lake workspace for sandbox verification."""

from __future__ import annotations

import shutil
from pathlib import Path

from lemma.problems.base import Problem


def materialize_workspace(dest: Path, problem: Problem, submission_lean: str) -> None:
    """
    Write Challenge, Solution, Submission, lakefile, toolchain, and axiom check driver.

    ``dest`` must be empty or will be created; caller typically uses a temp directory.
    """
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    (dest / "Challenge.lean").write_text(problem.challenge_source(), encoding="utf-8")
    (dest / "Solution.lean").write_text(problem.solution_source(), encoding="utf-8")
    (dest / "Submission.lean").write_text(submission_lean, encoding="utf-8")

    (dest / "lean-toolchain").write_text(problem.lean_toolchain.strip() + "\n", encoding="utf-8")

    lake = f'''name = "lemma_round"
version = "0.1.0"
defaultTargets = ["Challenge", "Solution", "Submission"]

[leanOptions]
autoImplicit = false

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "{problem.mathlib_rev}"

[[lean_lib]]
name = "Challenge"

[[lean_lib]]
name = "Solution"

[[lean_lib]]
name = "Submission"
'''
    (dest / "lakefile.toml").write_text(lake, encoding="utf-8")

    thm = problem.theorem_name
    # Check axioms on the miner's theorem in ``Submission`` (not ``Solution``): the
    # Solution module only bridges Challenge ↔ Submission and may not expose names
    # the way ``lake env lean`` expects for every workspace layout.
    axiom_check = f"""import Submission

#print axioms Submission.{thm}
"""
    (dest / "AxiomCheck.lean").write_text(axiom_check, encoding="utf-8")
