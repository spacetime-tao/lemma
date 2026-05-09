"""Run Lean verification inside Docker (or optionally on host)."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import BaseModel

from lemma.lean.cheats import (
    axiom_scan_ok,
    cheat_scan_stderr_tail,
    lake_build_environment_failed,
    lean_driver_failed,
    scan_submission_for_cheats,
)
from lemma.lean.comparator_hook import hook_failure_reason, run_comparator_hook
from lemma.lean.proof_metrics import (
    LeanProofMetrics,
    collect_host_proof_metrics,
    docker_proof_metrics_shell_fragment,
    parse_proof_metrics_line,
)
from lemma.lean.workspace import materialize_workspace, workspace_verify_cache_key
from lemma.problems.base import Problem


@lru_cache(maxsize=512)
def _template_slot_lock(cache_key: str) -> threading.RLock:
    """Serialize in-place verify + cache publish for one theorem template (reentrant for nested publish)."""
    return threading.RLock()


def _clone_dot_lake(src: Path, dst: Path) -> None:
    """Clone ``.lake`` for an isolated build tree.

    Plain ``shutil.copytree`` duplicates gigabytes on every verify (slow). On APFS (macOS)
    ``cp -cR`` uses copy-on-write clones when possible — fast and **independent** trees (Lake
    may write during ``lake build``, so we must not use ``os.link`` sharing with the slot).
    Linux tries ``cp --reflink=auto`` (btrfs/xfs). Falls back to a full copy.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        shutil.rmtree(dst)
    if sys.platform == "darwin":
        try:
            subprocess.run(
                ["cp", "-cR", str(src), str(dst)],
                check=True,
                timeout=7200,
                capture_output=True,
            )
            return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
    if sys.platform.startswith("linux"):
        try:
            subprocess.run(
                ["cp", "-a", "--reflink=auto", str(src), str(dst)],
                check=True,
                timeout=7200,
                capture_output=True,
            )
            return
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            pass
    shutil.copytree(src, dst, symlinks=True, dirs_exist_ok=True)


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def _lean_num_threads_value() -> str:
    """Threads for Lean's runtime pool ([docs](https://lean-lang.org/doc/reference/latest/IO/Tasks-and-Threads/)).

    Override with ``LEMMA_LEAN_NUM_THREADS``. Default: logical cores (cap 64).
    """
    raw = os.environ.get("LEMMA_LEAN_NUM_THREADS", "").strip()
    if raw:
        return raw
    return str(min(64, max(1, os.cpu_count() or 8)))


def _lean_env_exports_bash() -> str:
    """Shell preamble so ``lake`` / ``lean`` inside Docker see ``LEAN_NUM_THREADS``."""
    n = _lean_num_threads_value()
    return f"export LEAN_NUM_THREADS={shlex.quote(n)}; "


def _merge_lean_process_env(base: dict[str, str]) -> dict[str, str]:
    """Ensure subprocess lake/lean runs with an explicit ``LEAN_NUM_THREADS`` when unset."""
    out = dict(base)
    if "LEAN_NUM_THREADS" not in out:
        out["LEAN_NUM_THREADS"] = _lean_num_threads_value()
    return out


def _lake_build_argv() -> list[str]:
    """Verify needs ``Submission`` (+ Mathlib deps). Full ``lake build`` is optional (CI / debugging)."""
    if _env_truthy("LEMMA_LEAN_VERIFY_FULL_BUILD"):
        return ["lake", "build"]
    return ["lake", "build", "Submission"]


def _lake_build_shell_fragment() -> str:
    """Shell snippet for Docker ``bash -lc`` (same semantics as :func:`_lake_build_argv`)."""
    if _env_truthy("LEMMA_LEAN_VERIFY_FULL_BUILD"):
        return "lake build"
    return "lake build Submission"


def _docker_network_allows_remote_cache(network_mode: str) -> bool:
    nm = (network_mode or "none").strip().lower()
    return nm not in ("none", "no", "")


def lake_exe_cache_get_needed(work: Path) -> bool:
    """Whether to run ``lake exe cache get`` — skip when Mathlib checkout already exists (warm workspace).

    Override with ``LEMMA_LEAN_ALWAYS_CACHE_GET=1`` (always fetch) or
    ``LEMMA_LEAN_SKIP_CACHE_GET_WHEN_WARM=0`` (always try fetch when networking allows).
    """
    if _env_truthy("LEMMA_LEAN_ALWAYS_CACHE_GET"):
        return True
    if os.environ.get("LEMMA_LEAN_SKIP_CACHE_GET_WHEN_WARM", "1").strip().lower() in (
        "0",
        "false",
        "no",
    ):
        return True
    return not (work / ".lake" / "packages" / "mathlib").is_dir()


def docker_worker_container_path(work: Path, host_root: Path, mount_point: Path) -> str:
    """Map a host workspace path to the path inside a worker container (same bind-mount root)."""
    rel = work.resolve().relative_to(Path(host_root).resolve())
    return str((mount_point / rel).as_posix())


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
    "remote_error",
    "comparator_rejected",
    "attest_trusted",
]


class VerifyResult(BaseModel):
    passed: bool
    reason: VerifyReason
    stderr_tail: str = ""
    stdout_tail: str = ""
    build_seconds: float = 0.0
    proof_metrics: LeanProofMetrics | None = None


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
        workspace_cache_dir: Path | None = None,
        docker_worker: str | None = None,
        workspace_cache_include_submission_hash: bool = False,
        proof_metrics_enabled: bool = False,
    ) -> None:
        self.image = image
        self.cpu = cpu
        self.mem_mb = mem_mb
        self.timeout_s = timeout_s
        self.network_mode = network_mode
        # Caller passes resolved preference (typically ``LemmaSettings.lean_use_docker``).
        self.use_docker = bool(use_docker)
        self.workspace_cache_dir = workspace_cache_dir
        self.workspace_cache_include_submission_hash = bool(workspace_cache_include_submission_hash)
        self.proof_metrics_enabled = bool(proof_metrics_enabled)
        # Prefer explicit constructor / LemmaSettings (`.env`); ``os.environ`` alone is not populated from
        # pydantic's dotenv load unless the process exported the variable.
        _dw = docker_worker if docker_worker is not None else os.environ.get("LEMMA_LEAN_DOCKER_WORKER")
        self.docker_worker = (_dw or "").strip()

    def verify(self, problem: Problem, submission_src: str) -> VerifyResult:
        cheat = scan_submission_for_cheats(submission_src)
        if not cheat.ok:
            return VerifyResult(
                passed=False,
                reason="cheat_token",
                stderr_tail=cheat_scan_stderr_tail(cheat),
            )

        # Warm cache: if the template slot already has `.lake`, verify **in that directory** under a
        # per-template lock. That avoids copying or cloning multi‑GB `.lake` trees (still slow on
        # APFS even with `cp -cR`). Cold path: fresh temp under the cache root (same volume as
        # `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` when set) and publish on first success.
        cache_key: str | None = None
        slot: Path | None = None
        work: Path | None = None
        inplace = False
        if self.workspace_cache_dir is not None:
            self.workspace_cache_dir.mkdir(parents=True, exist_ok=True)
            cache_key = workspace_verify_cache_key(
                problem,
                submission_src,
                include_submission_fingerprint=self.workspace_cache_include_submission_hash,
            )
            slot = self.workspace_cache_dir / cache_key
            if slot.is_dir() and (slot / ".lake").is_dir():
                work = slot
                inplace = True
                logger.debug("lean workspace cache hit template={} mode=in_place", cache_key)
            else:
                work = Path(tempfile.mkdtemp(prefix="lemma-lean-", dir=str(self.workspace_cache_dir)))
        else:
            work = Path(tempfile.mkdtemp(prefix="lemma-lean-"))

        try:
            if inplace:
                assert cache_key is not None and slot is not None
                with _template_slot_lock(cache_key):
                    materialize_workspace(
                        work,
                        problem,
                        submission_src,
                        preserve_lake=True,
                        include_proof_metrics_probe=self.proof_metrics_enabled,
                    )
                    if self.use_docker:
                        vr = self._verify_docker(work)
                    else:
                        vr = self._verify_host(work)
                    # Slot already owns `.lake`; no publish (would re-enter the same lock).
                    return vr

            materialize_workspace(
                work,
                problem,
                submission_src,
                preserve_lake=False,
                include_proof_metrics_probe=self.proof_metrics_enabled,
            )

            if self.use_docker:
                vr = self._verify_docker(work)
            else:
                vr = self._verify_host(work)

            if (
                vr.passed
                and self.workspace_cache_dir is not None
                and cache_key is not None
                and slot is not None
                and (work / ".lake").is_dir()
            ):
                self._publish_workspace_cache(slot, work, cache_key)

            return vr
        finally:
            if not inplace and work is not None:
                shutil.rmtree(work, ignore_errors=True)

    def _publish_workspace_cache(self, slot: Path, work: Path, key: str) -> None:
        """First passing verify for this template — save `.lake` for faster follow-ups."""
        root = self.workspace_cache_dir
        if root is None or not (work / ".lake").is_dir():
            return
        lock = _template_slot_lock(key)
        with lock:
            if (slot / ".lake").is_dir():
                return
        wip = root / f"._wip_{key}"
        try:
            shutil.rmtree(wip, ignore_errors=True)
            wip.mkdir(parents=True, exist_ok=True)
            _clone_dot_lake(work / ".lake", wip / ".lake")
        except OSError as e:
            logger.warning("lean workspace cache publish (copy) failed: {}", e)
            shutil.rmtree(wip, ignore_errors=True)
            return
        with lock:
            if (slot / ".lake").is_dir():
                shutil.rmtree(wip, ignore_errors=True)
                return
            try:
                wip.rename(slot)
                logger.debug("lean workspace cache primed template={}", key)
            except OSError:
                shutil.rmtree(wip, ignore_errors=True)

    def _maybe_lake_cache_get(self, work: Path, env: dict[str, str]) -> None:
        """Warm mathlib cache when possible (matches Docker stub workflow); ignore failures."""
        if os.environ.get("LEMMA_SKIP_LAKE_CACHE", "").strip().lower() in ("1", "true", "yes"):
            return
        if not lake_exe_cache_get_needed(work):
            logger.debug("skipping lake exe cache get — warm workspace at {}", work)
            return
        try:
            subprocess.run(
                ["lake", "exe", "cache", "get"],
                cwd=work,
                capture_output=True,
                text=True,
                timeout=min(float(self.timeout_s), 900.0),
                env=_merge_lean_process_env(env),
            )
        except (subprocess.TimeoutExpired, OSError):
            pass

    def _maybe_host_lake_cache_before_docker(self, work: Path) -> None:
        """Run ``lake exe cache get`` on the **host** so the bind-mounted workspace is warm.

        Useful when Docker uses ``network_mode=none`` (no Azure/Mathlib cache inside the container)
        but the operator has ``lake`` on PATH with Internet — artifacts land in ``work/.lake`` before
        ``docker run``. Toolchains should match the sandbox image to avoid Lake re-downloading.

        Opt-in: ``LEMMA_HOST_LAKE_CACHE_BEFORE_DOCKER=1``.
        """
        if not _env_truthy("LEMMA_HOST_LAKE_CACHE_BEFORE_DOCKER"):
            return
        if not shutil.which("lake"):
            logger.debug("LEMMA_HOST_LAKE_CACHE_BEFORE_DOCKER set but `lake` not on PATH; skipping prefetch")
            return
        t0 = time.perf_counter()
        self._maybe_lake_cache_get(work, os.environ.copy())
        logger.debug("lean host lake cache prefetch before docker: {:.2f}s", time.perf_counter() - t0)

    def _verify_host(self, work: Path) -> VerifyResult:
        t0 = time.monotonic()
        env = _merge_lean_process_env(os.environ.copy())
        self._maybe_lake_cache_get(work, env)
        try:
            r = subprocess.run(
                _lake_build_argv(),
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
        if r.returncode != 0:
            # Lake often prints errors on stdout; always merge both (same as Docker log merge).
            combined = ((r.stderr or "") + "\n" + (r.stdout or ""))[-16_000:]
            if lake_build_environment_failed(combined):
                return VerifyResult(
                    passed=False,
                    reason="compile_error",
                    stderr_tail=combined,
                    build_seconds=elapsed,
                )
            return VerifyResult(
                passed=False,
                reason="compile_error",
                stderr_tail=combined,
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
        proof_metrics = None
        if self.proof_metrics_enabled:
            proof_metrics = collect_host_proof_metrics(
                work,
                timeout_s=min(float(self.timeout_s), 120.0),
                env=env,
            )
        return VerifyResult(
            passed=True,
            reason="ok",
            stdout_tail=out[-2000:],
            build_seconds=elapsed,
            proof_metrics=proof_metrics,
        )

    def _docker_worker_host_root(self) -> Path | None:
        """Host directory that is bind-mounted at ``LEMMA_LEAN_DOCKER_WORKER_MOUNT`` in the worker container."""
        raw = os.environ.get("LEMMA_LEAN_DOCKER_WORKER_HOST_ROOT", "").strip()
        if raw:
            return Path(raw).expanduser().resolve()
        if self.workspace_cache_dir is not None:
            return self.workspace_cache_dir.resolve()
        return None

    def _docker_worker_mount_point(self) -> Path:
        mp = os.environ.get("LEMMA_LEAN_DOCKER_WORKER_MOUNT", "/lemma-workspace").strip()
        return Path(mp if mp else "/lemma-workspace")

    def _docker_verify_inner_script(self, work: Path) -> str:
        """Bash script run inside the sandbox (cwd = workspace): stub ``.lake``, build, axiom check."""
        lake_cache_prefix = ""
        if _docker_network_allows_remote_cache(self.network_mode):
            if lake_exe_cache_get_needed(work):
                lake_cache_prefix = "lake exe cache get && "
            else:
                logger.debug("docker verify: skipping lake exe cache get (warm packages/mathlib)")
        build_frag = _lake_build_shell_fragment()
        env_preamble = _lean_env_exports_bash()
        metrics_frag = ""
        if self.proof_metrics_enabled:
            metrics_frag = f"; {docker_proof_metrics_shell_fragment()}"
        return (
            f"{env_preamble}"
            "set -euo pipefail; "
            "if [ -d /opt/lemma-stub ] && [ ! -d .lake ]; then "
            "cp -a /opt/lemma-stub/.lake . 2>/dev/null || true; fi; "
            f"{lake_cache_prefix}{build_frag} && lake env lean AxiomCheck.lean{metrics_frag}"
        )

    def _verify_docker_parse_logs(
        self,
        text: str,
        exit_status: int,
        elapsed: float,
        work: Path,
        log_tail: int,
    ) -> VerifyResult:
        """Shared exit-code / log interpretation for one-shot containers and ``docker exec`` workers."""
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
        proof_metrics = parse_proof_metrics_line(text) if self.proof_metrics_enabled else None
        return VerifyResult(
            passed=True,
            reason="ok",
            stdout_tail=text[-2000:],
            build_seconds=elapsed,
            proof_metrics=proof_metrics,
        )

    def _verify_docker_cli_exec(
        self,
        worker: str,
        container_workdir: str,
        inner: str,
        work: Path,
        log_tail: int,
    ) -> VerifyResult:
        """Run the same inner script via ``docker exec`` into a long-lived worker (avoids per-job ``docker run``)."""
        full = f"cd {shlex.quote(container_workdir)} && {inner}"
        t0 = time.monotonic()
        try:
            r = subprocess.run(
                ["docker", "exec", worker, "bash", "-lc", full],
                capture_output=True,
                text=True,
                timeout=float(self.timeout_s),
            )
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - t0
            return VerifyResult(
                passed=False,
                reason="timeout",
                stderr_tail="docker exec timed out",
                build_seconds=elapsed,
            )
        elapsed = time.monotonic() - t0
        if _env_truthy("LEMMA_LEAN_VERIFY_TIMING"):
            logger.info(
                "lean verify timing docker_exec wall_s={:.3f} worker={} LEAN_NUM_THREADS={}",
                elapsed,
                worker,
                _lean_num_threads_value(),
            )
        text = ((r.stderr or "") + "\n" + (r.stdout or ""))[-64_000:]
        rc = r.returncode
        if rc is None:
            rc = -1
        return self._verify_docker_parse_logs(text, int(rc), elapsed, work, log_tail)

    def _verify_docker(self, work: Path) -> VerifyResult:
        try:
            import docker.errors
            from requests.exceptions import ReadTimeout
        except ImportError:
            return VerifyResult(passed=False, reason="docker_error", stderr_tail="docker SDK missing")

        import docker

        self._maybe_host_lake_cache_before_docker(work)

        inner = self._docker_verify_inner_script(work)
        log_tail = 16_000

        # Optional: long-lived worker + `docker exec` — avoids container create/start/remove overhead
        # (often hundreds of ms per verify on Linux, >1s on Docker Desktop). Requires the host root of the
        # workspace cache to match the worker bind-mount (see docs/validator.md).
        worker = self.docker_worker
        if worker and shutil.which("docker"):
            root = self._docker_worker_host_root()
            if root is None:
                logger.warning(
                    "LEMMA_LEAN_DOCKER_WORKER is set but no host cache root is configured — set "
                    "LEMMA_LEAN_DOCKER_WORKER_HOST_ROOT or LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR; "
                    "using one-shot container",
                )
            else:
                try:
                    cdir = docker_worker_container_path(work, root, self._docker_worker_mount_point())
                except ValueError:
                    logger.debug(
                        "docker worker skipped — {} is not under {}; using one-shot container",
                        work,
                        root,
                    )
                else:
                    logger.debug("lean docker verify via exec worker={} container_workdir={}", worker, cdir)
                    return self._verify_docker_cli_exec(worker, cdir, inner, work, log_tail)

        client = docker.from_env()
        nano_cpus = int(self.cpu * 1e9)
        mem = self.mem_mb * 1024 * 1024
        t0 = time.monotonic()
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
            if _env_truthy("LEMMA_LEAN_VERIFY_TIMING"):
                logger.info(
                    "lean verify timing docker_one_shot wall_s={:.3f} LEAN_NUM_THREADS={}",
                    elapsed,
                    _lean_num_threads_value(),
                )
            return self._verify_docker_parse_logs(text, exit_status, elapsed, work, log_tail)
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
