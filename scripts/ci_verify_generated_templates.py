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
"""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path


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


def _lake_build_only(work: Path, image: str, timeout_s: float) -> tuple[int, str]:
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
            demux=False,
            timeout=int(timeout_s),
            user="0:0",
        )
        text = out.decode("utf-8", errors="replace") if isinstance(out, bytes) else str(out)
        return 0, text
    except docker.errors.ContainerError as e:
        err_b = e.stderr or b""
        out_b = e.stdout or b""
        text = err_b.decode("utf-8", errors="replace") + out_b.decode("utf-8", errors="replace")
        return int(e.exit_status), text
    except Exception as e:
        return 1, str(e)


def main() -> int:
    if os.environ.get("RUN_DOCKER_LEAN_TEMPLATES", "").strip() not in ("1", "true", "yes"):
        print("SKIP: set RUN_DOCKER_LEAN_TEMPLATES=1 to run template compile checks", file=sys.stderr)
        return 0

    image = os.environ.get("LEAN_SANDBOX_IMAGE", "lemma/lean-sandbox:latest")
    timeout_s = float(os.environ.get("LEMMA_TEMPLATE_CI_TIMEOUT_S", "2400"))

    from lemma.lean.workspace import materialize_workspace
    from lemma.problems.generated import GeneratedProblemSource

    seed_map = _find_seed_per_builder()
    src = GeneratedProblemSource()
    failures: list[str] = []

    for bi in sorted(seed_map.keys()):
        seed = seed_map[bi]
        p = src.sample(seed)
        stub = p.submission_stub()
        tmp = Path(tempfile.mkdtemp(prefix="lemma-tpl-ci-"))
        try:
            materialize_workspace(tmp, p, stub)
            code, out = _lake_build_only(tmp, image, timeout_s)
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
