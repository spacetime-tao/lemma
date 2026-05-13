"""Workspace cache publishes and reuses in-place slots."""

import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from lemma.lean.sandbox import LeanSandbox, VerifyResult
from lemma.lean.workspace import workspace_verify_cache_key
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
    sub = """import Mathlib
namespace Submission
theorem t_test : True := by trivial
end Submission
"""
    cache = tmp_path / "ws_cache"
    key = workspace_verify_cache_key(p, sub, include_submission_fingerprint=False)
    slot = cache / key
    slot.mkdir(parents=True)
    (slot / ".lake").mkdir()
    (slot / ".lake" / "marker").write_text("warm", encoding="utf-8")

    seen: list[Path] = []

    def fake_host(self: LeanSandbox, work: Path) -> VerifyResult:  # noqa: ARG001
        seen.append(work.resolve())
        return VerifyResult(passed=True, reason="ok")

    monkeypatch.setattr(LeanSandbox, "_verify_host", fake_host)
    sb = LeanSandbox(use_docker=False, timeout_s=30, workspace_cache_dir=cache)
    vr = sb.verify(p, sub)
    assert vr.passed
    assert len(seen) == 1
    assert seen[0] == slot.resolve()
    assert (slot / ".lake" / "marker").read_text() == "warm"


def test_cold_cache_publish_moves_verified_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = _minimal_problem()
    sub = """import Mathlib
namespace Submission
theorem t_test : True := by trivial
end Submission
"""
    cache = tmp_path / "ws_cache"
    key = workspace_verify_cache_key(p, sub, include_submission_fingerprint=False)
    slot = cache / key
    seen: list[Path] = []

    def fake_host(self: LeanSandbox, work: Path) -> VerifyResult:  # noqa: ARG001
        seen.append(work)
        (work / ".lake" / "packages" / "mathlib").mkdir(parents=True)
        (work / ".lake" / "marker").write_text("primed", encoding="utf-8")
        return VerifyResult(passed=True, reason="ok")

    monkeypatch.setattr(LeanSandbox, "_verify_host", fake_host)
    sb = LeanSandbox(use_docker=False, timeout_s=30, workspace_cache_dir=cache)
    vr = sb.verify(p, sub)

    assert vr.passed
    assert len(seen) == 1
    assert not seen[0].exists()
    assert (slot / ".lake" / "marker").read_text(encoding="utf-8") == "primed"
    assert (slot / "Submission.lean").exists()


def test_cold_cache_keeps_warm_lake_after_proof_compile_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = _minimal_problem()
    sub = """import Mathlib
namespace Submission
theorem t_test : True := by
  exact False.elim
end Submission
"""
    cache = tmp_path / "ws_cache"
    key = workspace_verify_cache_key(p, sub, include_submission_fingerprint=False)
    slot = cache / key

    def fake_host(self: LeanSandbox, work: Path) -> VerifyResult:  # noqa: ARG001
        (work / ".lake" / "packages" / "mathlib").mkdir(parents=True)
        return VerifyResult(passed=False, reason="compile_error")

    monkeypatch.setattr(LeanSandbox, "_verify_host", fake_host)
    sb = LeanSandbox(use_docker=False, timeout_s=30, workspace_cache_dir=cache)
    vr = sb.verify(p, sub)

    assert not vr.passed
    assert (slot / ".lake" / "packages" / "mathlib").is_dir()
    assert (slot / "Submission.lean").exists()


def test_cold_cache_singleflight_warms_once_for_concurrent_template(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    p = _minimal_problem()
    sub_a = """import Mathlib
namespace Submission
theorem t_test : True := by trivial
end Submission
"""
    sub_b = """import Mathlib
namespace Submission
theorem t_test : True := by
  trivial
end Submission
"""
    cache = tmp_path / "ws_cache"
    key = workspace_verify_cache_key(p, sub_a, include_submission_fingerprint=False)
    slot = cache / key
    seen: list[Path] = []

    def fake_host(self: LeanSandbox, work: Path) -> VerifyResult:  # noqa: ARG001
        seen.append(work.resolve())
        if work != slot:
            time.sleep(0.05)
            (work / ".lake" / "packages" / "mathlib").mkdir(parents=True)
            (work / ".lake" / "marker").write_text("primed", encoding="utf-8")
        return VerifyResult(passed=True, reason="ok")

    monkeypatch.setattr(LeanSandbox, "_verify_host", fake_host)
    sb = LeanSandbox(use_docker=False, timeout_s=30, workspace_cache_dir=cache)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda sub: sb.verify(p, sub), [sub_a, sub_b]))

    assert [r.passed for r in results] == [True, True]
    assert len(seen) == 2
    assert seen[0] != slot.resolve()
    assert seen[1] == slot.resolve()
    assert (slot / ".lake" / "marker").read_text(encoding="utf-8") == "primed"


def test_proof_metrics_probe_materialized_in_warm_slot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    p = _minimal_problem()
    sub = """import Mathlib
namespace Submission
theorem t_test : True := by trivial
end Submission
"""
    cache = tmp_path / "ws_cache"
    key = workspace_verify_cache_key(p, sub, include_submission_fingerprint=False)
    slot = cache / key
    slot.mkdir(parents=True)
    (slot / ".lake").mkdir()

    def fake_host(self: LeanSandbox, work: Path) -> VerifyResult:  # noqa: ARG001
        assert (work / "ProofMetrics.lean").exists()
        return VerifyResult(passed=True, reason="ok")

    monkeypatch.setattr(LeanSandbox, "_verify_host", fake_host)
    sb = LeanSandbox(use_docker=False, timeout_s=30, workspace_cache_dir=cache, proof_metrics_enabled=True)
    vr = sb.verify(p, sub)
    assert vr.passed
