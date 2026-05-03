"""Catalog parsers and Problem rows with ``challenge_full``."""

import json
from pathlib import Path

from lemma.catalog.minif2f_parse import collect_minif2f_layout
from lemma.catalog.putnam import parse_putnam_file
from lemma.problems.minif2f import MiniF2FSource


def test_collect_minif2f_single_file_layout(tmp_path: Path) -> None:
    """google-deepmind/miniF2F uses ``MiniF2F/Test.lean`` instead of ``MiniF2F/Test/*.lean``."""
    mini = tmp_path / "MiniF2F"
    mini.mkdir()
    (mini / "Test.lean").write_text(
        "theorem smoke_single_file : True := by\n  sorry\n",
        encoding="utf-8",
    )
    rows = collect_minif2f_layout(tmp_path)
    assert len(rows) == 1
    assert rows[0]["theorem_name"] == "smoke_single_file"
    assert rows[0]["split"] == "test"


def test_putnam_parse_sample(tmp_path: Path) -> None:
    lean = tmp_path / "putnam_1962_a1.lean"
    lean.write_text(
        """import Mathlib

open MeasureTheory

theorem putnam_1962_a1 (S : Set Nat) (h : S.Nonempty) : True :=
sorry
""",
        encoding="utf-8",
    )
    row = parse_putnam_file(lean)
    assert row is not None
    assert row["theorem_name"] == "putnam_1962_a1"
    assert "challenge_full" in row
    assert "Submission.putnam_1962_a1" in row["solution_full"]


def test_problem_challenge_full_roundtrip(tmp_path: Path) -> None:
    row = {
        "id": "t/challenge_full_smoke",
        "theorem_name": "foo",
        "type_expr": "smoke",
        "split": "test",
        "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
        "mathlib_rev": "5450b53e5ddc",
        "imports": [],
        "challenge_full": "theorem foo : True := by\n  sorry",
        "solution_full": (
            "import Submission\n\ntheorem LemmaSubmissionBridge : True := by\n  exact Submission.foo"
        ),
        "submission_stub": (
            "import Mathlib\n\nnamespace Submission\n\ntheorem foo : True := by\n  sorry\n\nend Submission\n"
        ),
    }
    path = tmp_path / "one.json"
    path.write_text(json.dumps([row], indent=2), encoding="utf-8")
    src = MiniF2FSource(path)
    p = src.get("t/challenge_full_smoke")
    assert "theorem foo" in p.challenge_source()
    assert "exact Submission.foo" in p.solution_source()
