"""Run Lean verification inside Docker (or optionally on host)."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from lemma.lean.cheats import (
    axiom_scan_ok,
    lake_build_environment_failed,
    lean_driver_failed,
    scan_submission_for_cheats,
)
from lemma.lean.comparator_hook import hook_failure_reason, run_comparator_hook
from lemma.lean.workspace import materialize_workspace
from lemma.problems.base import Problem


def _docker_container_logs_text(container: object) -> str:
    """Merge stdout+stderr from ``container.logs()`` (Lake often prints failures to stdout)."""
    raw = container.logs(stdout=True, stderr=True, timestamps=False)
    if isinstance(raw, tuple):
        out_b, err_b = raw
        return (
            (out_b or b"").decode("utf-8", errors="replace")
            + "\n"
            + (err_b or b"").decode("utf-8", errors="replace")
        )
    return raw.decode("utf-8", errors="replace")


VerifyReason = Literal[
    "ok",
    "compile_error",
    "axiom_violation",
    "cheat_token",
    "timeout",
    "oom",
    "docker_error",
    "comparator_rejected",
]


class VerifyResult(BaseModel):
    passed: bool
    reason: VerifyReason
    stderr_tail: str = ""
    stdout_tail: str = ""
    build_seconds: float = 0.0


class LeanSandbox:
    """Verify ``Submission.lean`` against a ``Problem`` in an isolated environment."""

    def __init__(
        self,
        image: str = "lemma/lean-sandbox:latest",
        cpu: float = 2.0,
        mem_mb: int = 8192,
        timeout_s: int = 600,
        network_mode: str = "none",
        use_docker: bool = True,
    ) -> None:
        self.image = image
        self.cpu = cpu
        self.mem_mb = mem_mb
        self.timeout_s = timeout_s
        self.network_mode = network_mode
        self.use_docker = use_docker and os.environ.get("LEMMA_USE_DOCKER", "1") != "0"

    def verify(self, problem: Problem, submission_src: str) -> VerifyResult:
        cheat = scan_submission_for_cheats(submission_src)
        if not cheat.ok:
            return VerifyResult(passed=False, reason="cheat_token", stderr_tail=cheat.reason or "")

        tmp = Path(tempfile.mkdtemp(prefix="lemma-lean-"))
        try:
            materialize_workspace(tmp, problem, submission_src)
            if self.use_docker:
                return self._verify_docker(tmp)
            return self._verify_host(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def _maybe_lake_cache_get(self, work: Path, env: dict[str, str]) -> None:
        """Warm mathlib cache when possible (matches Docker stub workflow); ignore failures."""
        if os.environ.get("LEMMA_SKIP_LAKE_CACHE", "").strip().lower() in ("1", "true", "yes"):
            return
        try:
            subprocess.run(
                ["lake", "exe", "cache", "get"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=min(float(self.timeout_s), 900.0),
                env=env,
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    def _verify_host(self, work: Path) -> VerifyResult:
        t0 = time.monotonic()
        env = os.environ.copy()
        self._maybe_lake_cache_get(work, env)
        try:
            r = subprocess.run(
                ["lake", "build"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                env=env,
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(passed=False, reason="timeout", stderr_tail="lake build timeout")
        except OSError as e:
            return VerifyResult(passed=False, reason="docker_error", stderr_tail=str(e))

        elapsed = time.monotonic() - t0
        tail = (r.stderr or "")[-4000:]
        if r.returncode != 0:
            combined = ((r.stderr or "") + "\n" + (r.stdout or ""))[-8000:]
            if lake_build_environment_failed(combined):
                return VerifyResult(
                    passed=False,
                    reason="compile_error",
                    stderr_tail=combined[-4000:],
                    build_seconds=elapsed,
                )
            return VerifyResult(
                passed=False,
                reason="compile_error",
                stderr_tail=tail,
                build_seconds=elapsed,
            )

        try:
            r2 = subprocess.run(
                ["lake", "env", "lean", str(work / "AxiomCheck.lean")],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=min(self.timeout_s, 120),
                env=env,
            )
        except subprocess.TimeoutExpired:
            return VerifyResult(passed=False, reason="timeout", stderr_tail="axiom check timeout")
        out = (r2.stdout or "") + "\n" + (r2.stderr or "")
        if lake_build_environment_failed(out):
            return VerifyResult(
                passed=False,
                reason="compile_error",
                stderr_tail=out[-4000:],
                stdout_tail=out[-4000:],
                build_seconds=elapsed,
            )
        ok, found = axiom_scan_ok(out)
        if not ok:
            extra = f" axioms={found}" if found else ""
            # Parse failure (found is None) means no usable #print axioms line — usually lake/Lean failed.
            if found is None or lean_driver_failed(out):
                return VerifyResult(
                    passed=False,
                    reason="compile_error",
                    stderr_tail=(out[-4000:] + extra),
                    stdout_tail=out[-4000:],
                    build_seconds=elapsed,
                )
            return VerifyResult(
                passed=False,
                reason="axiom_violation",
                stderr_tail=(out[-4000:] + extra),
                stdout_tail=out[-4000:],
                build_seconds=elapsed,
            )
        hook = run_comparator_hook(work, timeout_s=float(self.timeout_s))
        if hook is not None and hook_failure_reason(hook):
            return VerifyResult(
                passed=False,
                reason="comparator_rejected",
                stderr_tail=hook.stderr_tail[-8000:],
                build_seconds=elapsed,
            )
        return VerifyResult(passed=True, reason="ok", stdout_tail=out[-2000:], build_seconds=elapsed)

    def _verify_docker(self, work: Path) -> VerifyResult:
        try:
            import docker.errors
            from requests.exceptions import ReadTimeout
        except ImportError:
            return VerifyResult(passed=False, reason="docker_error", stderr_tail="docker SDK missing")

        import docker

        client = docker.from_env()
        inner = (
            "set -euo pipefail; "
            "if [ -d /opt/lemma-stub ]; then cp -a /opt/lemma-stub/.lake . 2>/dev/null || true; fi; "
            "lake build && lake env lean AxiomCheck.lean"
        )
        nano_cpus = int(self.cpu * 1e9)
        mem = self.mem_mb * 1024 * 1024
        t0 = time.monotonic()
        log_tail = 16_000
        container = None
        try:
            container = client.containers.create(
                image=self.image,
                command=["bash", "-lc", inner],
                volumes={str(work.resolve()): {"bind": "/work", "mode": "rw"}},
                working_dir="/work",
                network_mode=self.network_mode,
                nano_cpus=nano_cpus,
                mem_limit=mem,
                user="0:0",
            )
            container.start()
            try:
                wait_result = container.wait(timeout=float(self.timeout_s))
            except ReadTimeout:
                elapsed = time.monotonic() - t0
                try:
                    container.kill()
                except Exception:
                    pass
                text = _docker_container_logs_text(container)
                return VerifyResult(
                    passed=False,
                    reason="timeout",
                    stderr_tail=text[-log_tail:],
                    build_seconds=elapsed,
                )
            elapsed = time.monotonic() - t0
            text = _docker_container_logs_text(container)
            exit_status = (
                int(wait_result["StatusCode"]) if isinstance(wait_result, dict) else int(wait_result)
            )

            if exit_status != 0:
                if exit_status == 137:
                    return VerifyResult(
                        passed=False,
                        reason="oom",
                        stderr_tail=text[-log_tail:],
                        build_seconds=elapsed,
                    )
                if lake_build_environment_failed(text):
                    return VerifyResult(
                        passed=False,
                        reason="compile_error",
                        stderr_tail=text[-log_tail:],
                        build_seconds=elapsed,
                    )
                ok_ax, found_ax = axiom_scan_ok(text)
                if not ok_ax:
                    if found_ax is None or lean_driver_failed(text):
                        return VerifyResult(
                            passed=False,
                            reason="compile_error",
                            stderr_tail=text[-log_tail:],
                            build_seconds=elapsed,
                        )
                    extra_ax = f" axioms={found_ax}"
                    return VerifyResult(
                        passed=False,
                        reason="axiom_violation",
                        stderr_tail=text[-log_tail:] + extra_ax,
                        build_seconds=elapsed,
                    )
                return VerifyResult(
                    passed=False,
                    reason="compile_error",
                    stderr_tail=text[-log_tail:],
                    build_seconds=elapsed,
                )

            if lake_build_environment_failed(text):
                return VerifyResult(
                    passed=False,
                    reason="compile_error",
                    stderr_tail=text[-log_tail:],
                    build_seconds=elapsed,
                )
            ok, found = axiom_scan_ok(text)
            if not ok:
                extra = f" axioms={found}" if found else ""
                if found is None or lean_driver_failed(text):
                    return VerifyResult(
                        passed=False,
                        reason="compile_error",
                        stderr_tail=text[-log_tail:] + extra,
                        build_seconds=elapsed,
                    )
                return VerifyResult(
                    passed=False,
                    reason="axiom_violation",
                    stdout_tail=text[-4000:] + extra,
                    build_seconds=elapsed,
                )
            hook = run_comparator_hook(work, timeout_s=float(self.timeout_s))
            if hook is not None and hook_failure_reason(hook):
                return VerifyResult(
                    passed=False,
                    reason="comparator_rejected",
                    stderr_tail=hook.stderr_tail[-8000:],
                    build_seconds=elapsed,
                )
            return VerifyResult(passed=True, reason="ok", stdout_tail=text[-2000:], build_seconds=elapsed)
        except docker.errors.APIError as e:
            elapsed = time.monotonic() - t0
            return VerifyResult(
                passed=False,
                reason="docker_error",
                stderr_tail=str(e)[-8000:],
                build_seconds=elapsed,
            )
        except Exception as e:  # noqa: BLE001 — surface docker failures
            elapsed = time.monotonic() - t0
            err = str(e)
            if "timeout" in err.lower() or "timed out" in err.lower():
                return VerifyResult(passed=False, reason="timeout", stderr_tail=err, build_seconds=elapsed)
            if "137" in err or "OOM" in err or "non-zero exit: 137" in err:
                return VerifyResult(passed=False, reason="oom", stderr_tail=err, build_seconds=elapsed)
            return VerifyResult(passed=False, reason="docker_error", stderr_tail=err[-8000:], build_seconds=elapsed)
        finally:
            if container is not None:
                try:
                    container.remove(force=True)
                except Exception:
                    pass
