"""Host Lean verification (optional)."""

import os
import shutil

import pytest
from lemma.lean.sandbox import LeanSandbox
from lemma.problems.base import Problem

pytestmark = pytest.mark.skipif(
    not shutil.which("lake") or os.environ.get("LEMMA_RUN_HOST_LEAN") != "1",
    reason="set LEMMA_RUN_HOST_LEAN=1 and install elan/lake to run",
)


def test_verify_two_plus_two_rfl() -> None:
    p = Problem(
        id="test/local_two_plus_two",
        theorem_name="two_plus_two_eq_four",
        type_expr="(2 : Nat) + 2 = 4",
        split="test",
        lean_toolchain="leanprover/lean4:v4.30.0-rc2",
        mathlib_rev="5450b53e5ddc",
        imports=("Mathlib",),
    )
    submission = """import Mathlib

namespace Submission

theorem two_plus_two_eq_four : (2 : Nat) + 2 = 4 := by rfl

end Submission
"""
    sb = LeanSandbox(use_docker=False, timeout_s=900, proof_metrics_enabled=True)
    vr = sb.verify(p, submission)
    assert vr.passed, vr.stderr_tail + vr.stdout_tail
    assert vr.proof_metrics is not None
    assert vr.proof_metrics.probe_exit_code == 0
    assert vr.proof_metrics.proof_declaration_bytes > 0
    assert vr.proof_metrics.proof_declaration_lines > 0
