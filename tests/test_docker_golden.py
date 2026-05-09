"""Docker sandbox golden path (opt-in)."""

import os

import pytest

pytestmark = pytest.mark.docker


@pytest.mark.skipif(os.environ.get("RUN_DOCKER_LEAN") != "1", reason="set RUN_DOCKER_LEAN=1")
def test_docker_two_plus_two() -> None:
    from lemma.lean.sandbox import LeanSandbox
    from lemma.problems.base import Problem

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
    # Fresh workspaces often run ``lake`` against Mathlib over HTTPS; ``network_mode=none``
    # blocks DNS (see docs/validator.md — bridge only when bootstrap needs the network).
    sb = LeanSandbox(
        image=os.environ.get("LEAN_SANDBOX_IMAGE", "lemma/lean-sandbox:latest"),
        use_docker=True,
        network_mode=os.environ.get("LEAN_SANDBOX_NETWORK", "bridge"),
        timeout_s=1200,
        proof_metrics_enabled=True,
    )
    vr = sb.verify(p, submission)
    assert vr.passed, vr.stderr_tail
    assert vr.proof_metrics is not None
    assert vr.proof_metrics.probe_exit_code == 0
    assert vr.proof_metrics.proof_declaration_bytes > 0
    assert vr.proof_metrics.proof_declaration_lines > 0
