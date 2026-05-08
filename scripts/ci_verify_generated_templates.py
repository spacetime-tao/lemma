#!/usr/bin/env python3
"""Compile-check every generated template: ``lake build`` with Submission stub (``sorry``).

Why this exists (mainnet mindset): Python tests don't catch a bad Mathlib line in a template.
Wrong syntax ⇒ miners and validators disagree or builds fail in production.

This does **not** prove each theorem is solvable without ``sorry``—only that the workspace **parses
and typechecks** far enough for Lake to build libraries.

Run after building the sandbox image, e.g.::

    LEAN_SANDBOX_IMAGE=lemma-lean-sandbox:ci RUN_DOCKER_LEAN_TEMPLATES=1 \\
      uv run python scripts/ci_verify_generated_templates.py

Requires Docker; enable network so ``lake exe cache get`` can run when needed.

**Implementation:** all templates are merged into **one** Lake workspace (one Challenge / Solution /
Submission with every theorem). A single ``lake build`` checks every builder shape. Running 22
separate workspaces used to repeat Mathlib fetch/build and often failed CI (timeout, disk, flaky
network).
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

from lemma.problems.base import Problem


def _find_seed_per_builder() -> dict[int, int]:
    import lemma.problems.generated as reg

    need = len(reg._RAW_BUILDERS)
    GeneratedProblemSource = reg.GeneratedProblemSource
    src = GeneratedProblemSource()
    found: dict[int, int] = {}
    # Brute-force seeds until each builder_index appears (deterministic RNG).
    for seed in range(500_000):
        p = src.sample(seed)
        bi = p.extra.get("builder_index")
        if isinstance(bi, int) and bi not in found:
            found[bi] = seed
        if len(found) >= need:
            break
    if len(found) < need:
        raise RuntimeError(f"could not cover all builders: got {len(found)}/{need}")
    return found


def _materialize_multiplex(dest: Path, problems: list[Problem]) -> None:
    """One workspace containing every generated template (stubs). Same layout as round workspaces."""
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    p0 = problems[0]
    challenge_chunks: list[str] = []
    for p in problems:
        cf = p.extra.get("challenge_full")
        if not isinstance(cf, str) or not cf.strip():
            raise RuntimeError(f"missing challenge_full for builder problem id={p.id}")
        challenge_chunks.append(cf.strip())

    challenge = "import Mathlib\n\n" + "\n\n".join(challenge_chunks) + "\n"

    sol_theorems = "\n\n".join(
        f"theorem {p.theorem_name} : {p.type_expr} := by\n  exact Submission.{p.theorem_name}"
        for p in problems
    )
    solution = f"import Mathlib\nimport Submission\n\n{sol_theorems}\n"

    sub_theorems = "\n\n".join(
        f"theorem {p.theorem_name} : {p.type_expr} := by\n  sorry" for p in problems
    )
    submission = f"import Mathlib\n\nnamespace Submission\n\n{sub_theorems}\n\nend Submission\n"

    (dest / "Challenge.lean").write_text(challenge, encoding="utf-8")
    (dest / "Solution.lean").write_text(solution, encoding="utf-8")
    (dest / "Submission.lean").write_text(submission, encoding="utf-8")
    (dest / "lean-toolchain").write_text(p0.lean_toolchain.strip() + "\n", encoding="utf-8")

    lake = f'''name = "lemma_stub"
version = "0.1.0"
defaultTargets = ["Challenge", "Solution", "Submission"]

[leanOptions]
autoImplicit = false

[[require]]
name = "mathlib"
git = "https://github.com/leanprover-community/mathlib4.git"
rev = "{p0.mathlib_rev}"

[[lean_lib]]
name = "Challenge"

[[lean_lib]]
name = "Solution"

[[lean_lib]]
name = "Submission"
'''
    (dest / "lakefile.toml").write_text(lake, encoding="utf-8")


def _bisect_multiplex_failures(problems: list[Problem], image: str, *, initial_log_tail: str) -> list[str]:
    """Find failing template(s) without N separate workspaces (saves CI disk).

    When the all-in-one multiplex fails, binary-search which subset fails so we only run
    ``O(log n)`` multiplex builds, each in its own temp dir that is deleted immediately.
    """
    messages: list[str] = []

    def isolate(batch: list[Problem]) -> None:
        if len(batch) == 1:
            tmp = Path(tempfile.mkdtemp(prefix="lemma-tpl-bisect-"))
            try:
                _materialize_multiplex(tmp, batch)
                code, out = _lake_build_only(tmp, image)
                if code != 0:
                    p = batch[0]
                    bi = p.extra.get("builder_index")
                    messages.append(
                        f"ISOLATED FAIL builder_index={bi} id={p.id} "
                        f"template_fn={p.extra.get('template_fn')} exit={code}\n{out[-16000:]}"
                    )
                else:
                    messages.append(
                        f"ISOLATED OK builder_index={batch[0].extra.get('builder_index')} "
                        f"id={batch[0].id} — passes alone; failure may be interaction with other "
                        f"theorems in multiplex or flake. Multiplex tail:\n{initial_log_tail[-8000:]}"
                    )
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            return

        mid = len(batch) // 2
        left, right = batch[:mid], batch[mid:]
        tmp_l = Path(tempfile.mkdtemp(prefix="lemma-tpl-bisect-"))
        try:
            _materialize_multiplex(tmp_l, left)
            code_l, out_l = _lake_build_only(tmp_l, image)
        finally:
            shutil.rmtree(tmp_l, ignore_errors=True)

        if code_l != 0:
            isolate(left)
            return

        tmp_r = Path(tempfile.mkdtemp(prefix="lemma-tpl-bisect-"))
        try:
            _materialize_multiplex(tmp_r, right)
            code_r, out_r = _lake_build_only(tmp_r, image)
        finally:
            shutil.rmtree(tmp_r, ignore_errors=True)

        if code_r != 0:
            isolate(right)
            return

        messages.append(
            "Bisection: both halves built OK in isolation but full multiplex failed — "
            "possible cross-theorem name clash or CI flake.\n"
            f"Left multiplex log tail:\n{out_l[-6000:]}\n---\nRight multiplex log tail:\n"
            f"{out_r[-6000:]}\n---\nFull multiplex tail:\n{initial_log_tail[-8000:]}"
        )

    isolate(problems)
    return messages


def _lake_build_only(work: Path, image: str) -> tuple[int, str]:
    """Return (exit_code, combined_output)."""
    inner = (
        "set -euo pipefail; "
        "lake exe cache get || true; "
        "lake build"
    )
    try:
        import docker
        import docker.errors
    except ImportError as e:
        raise RuntimeError("docker SDK required") from e

    client = docker.from_env()
    try:
        out = client.containers.run(
            image,
            command=["bash", "-lc", inner],
            volumes={str(work.resolve()): {"bind": "/work", "mode": "rw"}},
            working_dir="/work",
            network_mode="bridge",
            remove=True,
            stdout=True,
            stderr=True,
            user="0:0",
        )
        text = out.decode("utf-8", errors="replace") if isinstance(out, bytes) else str(out)
        return 0, text
    except docker.errors.ContainerError as e:
        # docker SDK exposes ``stderr`` on ContainerError; ``stdout`` is not guaranteed.
        err_b = getattr(e, "stderr", b"") or b""
        out_b = getattr(e, "stdout", b"") or b""
        if not err_b and hasattr(e, "container") and e.container is not None:
            try:
                err_b = e.container.logs(stdout=False, stderr=True) or b""
                if not out_b:
                    out_b = e.container.logs(stdout=True, stderr=False) or b""
            except Exception:
                pass
        text = err_b.decode("utf-8", errors="replace") + out_b.decode("utf-8", errors="replace")
        return int(getattr(e, "exit_status", 1)), text
    except Exception as e:
        return 1, str(e)


def main() -> int:
    if os.environ.get("RUN_DOCKER_LEAN_TEMPLATES", "").strip() not in ("1", "true", "yes"):
        print("SKIP: set RUN_DOCKER_LEAN_TEMPLATES=1 to run template compile checks", file=sys.stderr)
        return 0

    image = os.environ.get("LEAN_SANDBOX_IMAGE", "lemma/lean-sandbox:latest")

    from lemma.problems.generated import GeneratedProblemSource

    seed_map = _find_seed_per_builder()
    src = GeneratedProblemSource()
    problems = [src.sample(seed_map[bi]) for bi in sorted(seed_map.keys())]

    if os.environ.get("CI_TEMPLATE_MULTIPLEX", "1").strip() not in ("0", "false", "no"):
        tmp = Path(tempfile.mkdtemp(prefix="lemma-tpl-ci-"))
        try:
            _materialize_multiplex(tmp, problems)
            code, out = _lake_build_only(tmp, image)
            if code != 0:
                print(
                    f"TEMPLATE BUILD FAILURE (multiplex, {len(problems)} theorems) exit={code}\n{out[-20000:]}",
                    file=sys.stderr,
                )
                print(
                    "Bisecting multiplex subsets (disk-friendly) to isolate failing builder(s)...",
                    file=sys.stderr,
                )
                for msg in _bisect_multiplex_failures(problems, image, initial_log_tail=out):
                    print(msg, "\n---\n", file=sys.stderr)
                return 1
            print(f"OK: {len(problems)} generated templates lake build in one workspace ({image})")
            return 0
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    # Slow / disk-heavy: one workspace per template (only when multiplex disabled).
    print(
        "WARN: CI_TEMPLATE_MULTIPLEX=0 — per-template Docker builds (high disk use).",
        file=sys.stderr,
    )
    from lemma.lean.workspace import materialize_workspace

    failures: list[str] = []
    for bi in sorted(seed_map.keys()):
        seed = seed_map[bi]
        p = src.sample(seed)
        stub = p.submission_stub()
        tmp = Path(tempfile.mkdtemp(prefix="lemma-tpl-ci-"))
        try:
            materialize_workspace(tmp, p, stub)
            code, out = _lake_build_only(tmp, image)
            if code != 0:
                failures.append(
                    f"builder_index={bi} seed={seed} template_fn={p.extra.get('template_fn')} "
                    f"exit={code}\n{out[-12000:]}"
                )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if failures:
        print("TEMPLATE BUILD FAILURES:\n", file=sys.stderr)
        for f in failures:
            print(f, "\n---\n", file=sys.stderr)
        return 1

    print(f"OK: {len(seed_map)} generated templates lake build successfully ({image})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1) from e
