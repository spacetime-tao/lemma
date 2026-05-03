"""Workspace cache uses in-place slot (no `.lake` clone) when primed."""

from pathlib import Path

import pytest
from lemma.lean.sandbox import LeanSandbox, VerifyResult
from lemma.lean.workspace import workspace_template_cache_key
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


def test_warm_cache_verifies_in_slot_dir_not_temp(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = _minimal_problem()
    cache = tmp_path / "ws_cache"
    key = workspace_template_cache_key(p)
    slot = cache / key
    slot.mkdir(parents=True)
    (slot / ".lake").mkdir()
    (slot / ".lake" / "marker").write_text("warm", encoding="utf-8")

    seen: list[Path] = []

    def fake_host(self: LeanSandbox, work: Path) -> VerifyResult:  # noqa: ARG001
        seen.append(work.resolve())
        return VerifyResult(passed=True, reason="ok")

    monkeypatch.setattr(LeanSandbox, "_verify_host", fake_host)
    sub = """import Mathlib
namespace Submission
theorem t_test : True := by trivial
end Submission
"""
    sb = LeanSandbox(use_docker=False, timeout_s=30, workspace_cache_dir=cache)
    vr = sb.verify(p, sub)
    assert vr.passed
    assert len(seen) == 1
    assert seen[0] == slot.resolve()
    assert (slot / ".lake" / "marker").read_text() == "warm"
