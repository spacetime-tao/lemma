from __future__ import annotations

from pathlib import Path

import pytest
from lemma.problems.base import Problem
from lemma.submissions import (
    load_pending_submissions,
    pending_submission_for_problem,
    save_pending_submission,
)


def _problem(type_expr: str = "True") -> Problem:
    return Problem(
        id="known/test/submission",
        theorem_name="target",
        type_expr=type_expr,
        split="known_theorems",
        lean_toolchain="lt",
        mathlib_rev="mr",
        imports=("Mathlib",),
    )


def test_save_pending_submission_stores_hashes_by_target(tmp_path: Path) -> None:
    path = tmp_path / "submissions.json"
    problem = _problem()

    entry = save_pending_submission(
        path,
        problem,
        "import Mathlib\n",
        proof_nonce="n" * 64,
        commitment_hash="c" * 64,
        commitment_status="committed",
        committed_block=10,
        commit_cutoff_block=34,
        reveal_block=35,
    )
    rows = load_pending_submissions(path)

    assert rows[problem.id] == entry
    assert entry.target_id == problem.id
    assert len(entry.proof_sha256) == 64
    assert entry.proof_script.endswith("\n")
    assert entry.proof_nonce == "n" * 64
    assert entry.commitment_hash == "c" * 64
    assert entry.commitment_status == "committed"
    assert entry.reveal_block == 35


def test_stale_submission_for_changed_statement_is_ignored(tmp_path: Path) -> None:
    path = tmp_path / "submissions.json"
    save_pending_submission(path, _problem("True"), "import Mathlib\n")

    assert pending_submission_for_problem(path, _problem("False")) is None


def test_empty_submission_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="empty"):
        save_pending_submission(tmp_path / "submissions.json", _problem(), "   ")
