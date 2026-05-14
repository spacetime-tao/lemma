"""Run Lean verify through the local sandbox."""

from __future__ import annotations

from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import LeanSandbox, VerifyResult
from lemma.problems.base import Problem


def lean_sandbox_from_settings(settings: LemmaSettings, verify_timeout_s: int) -> LeanSandbox:
    """Construct ``LeanSandbox`` from validator settings."""
    return LeanSandbox(
        image=settings.lean_sandbox_image,
        cpu=settings.lean_sandbox_cpu,
        mem_mb=settings.lean_sandbox_mem_mb,
        timeout_s=verify_timeout_s,
        network_mode=settings.lean_sandbox_network,
        use_docker=settings.lean_use_docker,
        workspace_cache_dir=settings.lean_verify_workspace_cache_dir,
        workspace_cache_max_dirs=settings.lemma_lean_workspace_cache_max_dirs,
        workspace_cache_max_bytes=settings.lemma_lean_workspace_cache_max_bytes,
    )


def run_lean_verify(
    settings: LemmaSettings,
    *,
    verify_timeout_s: int,
    problem: Problem,
    proof_script: str,
) -> VerifyResult:
    """Verify a submitted ``Submission.lean`` against a locked target."""
    return lean_sandbox_from_settings(settings, verify_timeout_s).verify(problem, proof_script)
