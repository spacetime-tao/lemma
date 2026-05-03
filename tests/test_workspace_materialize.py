"""Lake workspace materialize + template cache key."""

from pathlib import Path

from lemma.lean.workspace import materialize_workspace, workspace_template_cache_key
from lemma.problems.base import Problem


def _minimal_problem() -> Problem:
    return Problem(
        id="gen/test_k",
        theorem_name="t_test",
        type_expr="True",
        split="easy",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        imports=("Mathlib",),
    )


def test_workspace_template_cache_key_stable() -> None:
    p = _minimal_problem()
    assert workspace_template_cache_key(p) == workspace_template_cache_key(p)


def test_materialize_preserve_lake_keeps_dot_lake(tmp_path: Path) -> None:
    p = _minimal_problem()
    dest = tmp_path / "work"
    dest.mkdir()
    (dest / ".lake").mkdir()
    (dest / ".lake" / "warm_marker").write_text("ok", encoding="utf-8")
    materialize_workspace(dest, p, "namespace Submission\n", preserve_lake=True)
    assert (dest / ".lake" / "warm_marker").read_text() == "ok"
    assert (dest / "Submission.lean").read_text().startswith("namespace Submission")

