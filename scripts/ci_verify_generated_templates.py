#!/usr/bin/env python3
"""Gate every generated template, then optionally compile-check with ``lake build``.

Why this exists (mainnet mindset): Python tests don't catch a bad Mathlib line in a template.
Wrong syntax ⇒ miners and validators disagree or builds fail in production.

Without Docker, this script checks that every builder is reachable and has the metadata needed by
operators and registry pins, including a public witness proof. With
``RUN_DOCKER_LEAN_TEMPLATES=1``, it also builds the generated Challenge / Solution / Submission
workspace twice: first with ``sorry`` stubs, then with the public witness proofs and axiom checks.

The stub build proves every theorem statement is Lean-valid. The witness build proves each promoted
template has at least one complete, public proof under the pinned Lean/Mathlib image.

Run after building the sandbox image, e.g.::

    LEAN_SANDBOX_IMAGE=lemma-lean-sandbox:ci RUN_DOCKER_LEAN_TEMPLATES=1 \\
      uv run python scripts/ci_verify_generated_templates.py

Requires Docker; enable network so ``lake exe cache get`` can run when needed.

**Implementation:** all templates are merged into **one** Lake workspace (one Challenge / Solution /
Submission with every theorem). A single ``lake build`` checks every builder shape. Running separate
workspaces used to repeat Mathlib fetch/build and often failed CI (timeout, disk, flaky network).
"""

from __future__ import annotations

import itertools
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from lemma.lean.cheats import ALLOWED_AXIOMS
from lemma.problems.base import Problem
from lemma.problems.generated import generated_witness_submission_source

_VALID_SPLITS = {"easy", "medium", "hard", "extreme"}


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


def _sample_all_builders() -> list[tuple[int, int, Problem]]:
    """Return ``(builder_index, seed, problem)`` for one deterministic sample of every builder."""
    from lemma.problems.generated import GeneratedProblemSource

    seed_map = _find_seed_per_builder()
    src = GeneratedProblemSource()
    samples = [(bi, seed_map[bi], src.sample(seed_map[bi])) for bi in sorted(seed_map)]
    _validate_template_samples(samples)
    return samples


def _validate_template_samples(samples: list[tuple[int, int, Problem]]) -> None:
    """Cheap gate for builder wiring before the expensive Lean check."""
    errors: list[str] = []
    theorem_names: set[str] = set()
    for builder_index, seed, p in samples:
        errors.extend(_template_sample_errors(builder_index, seed, p))
        if p.theorem_name in theorem_names:
            errors.append(f"duplicate theorem_name={p.theorem_name!r}")
        theorem_names.add(p.theorem_name)
    if errors:
        raise RuntimeError("generated template metadata gate failed:\n- " + "\n- ".join(errors))


def _template_sample_errors(builder_index: int, seed: int, p: Problem) -> list[str]:
    errors: list[str] = []
    prefix = f"builder_index={builder_index} seed={seed} id={p.id}"
    if p.id != f"gen/{seed}":
        errors.append(f"{prefix}: expected id gen/{seed}")
    if p.extra.get("builder_index") != builder_index:
        errors.append(f"{prefix}: missing/mismatched extra.builder_index")
    template_fn = p.extra.get("template_fn")
    if not isinstance(template_fn, str) or not template_fn.startswith("_b_"):
        errors.append(f"{prefix}: missing extra.template_fn")
    informal = p.extra.get("informal_statement")
    if not isinstance(informal, str) or not informal.strip():
        errors.append(f"{prefix}: missing extra.informal_statement")
    elif informal == "Prove the displayed generated Lean theorem.":
        errors.append(f"{prefix}: informal_statement uses dashboard fallback text")
    if p.extra.get("source_lane") != "generated":
        errors.append(f"{prefix}: missing/mismatched extra.source_lane")
    if p.split not in _VALID_SPLITS:
        errors.append(f"{prefix}: invalid split {p.split!r}")
    if not p.theorem_name.strip():
        errors.append(f"{prefix}: empty theorem_name")
    if not p.type_expr.strip():
        errors.append(f"{prefix}: empty type_expr")
    if not p.lean_toolchain.strip():
        errors.append(f"{prefix}: empty lean_toolchain")
    if not p.mathlib_rev.strip():
        errors.append(f"{prefix}: empty mathlib_rev")
    challenge = p.extra.get("challenge_full")
    if not isinstance(challenge, str) or not challenge.strip():
        errors.append(f"{prefix}: missing challenge_full")
    else:
        if f"theorem {p.theorem_name}" not in challenge:
            errors.append(f"{prefix}: challenge_full does not declare theorem_name")
        if "sorry" not in challenge:
            errors.append(f"{prefix}: challenge_full must be a sorry stub")
    if f"exact Submission.{p.theorem_name}" not in p.solution_source():
        errors.append(f"{prefix}: solution bridge does not reference Submission.{p.theorem_name}")
    witness = p.extra.get("witness_proof")
    if not isinstance(witness, str) or not witness.strip():
        errors.append(f"{prefix}: missing witness_proof")
    elif "sorry" in witness or "admit" in witness:
        errors.append(f"{prefix}: witness_proof contains forbidden incomplete proof token")
    return errors


def _materialize_multiplex(dest: Path, problems: list[Problem], *, witness: bool) -> None:
    """One workspace containing every generated template. Same layout as round workspaces."""
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

    if witness:
        sub_theorems = "\n\n".join(
            generated_witness_submission_source(p)
            .removeprefix("import Mathlib\n\nnamespace Submission\n\n")
            .removesuffix("\nend Submission\n")
            .strip()
            for p in problems
        )
    else:
        sub_theorems = "\n\n".join(
            f"theorem {p.theorem_name} : {p.type_expr} := by\n  sorry" for p in problems
        )
    submission = f"import Mathlib\n\nnamespace Submission\n\n{sub_theorems}\n\nend Submission\n"

    (dest / "Challenge.lean").write_text(challenge, encoding="utf-8")
    (dest / "Solution.lean").write_text(solution, encoding="utf-8")
    (dest / "Submission.lean").write_text(submission, encoding="utf-8")
    (dest / "lean-toolchain").write_text(p0.lean_toolchain.strip() + "\n", encoding="utf-8")
    if witness:
        axiom_lines = "\n".join(f"#print axioms Submission.{p.theorem_name}" for p in problems)
        (dest / "AxiomCheck.lean").write_text(f"import Submission\n\n{axiom_lines}\n", encoding="utf-8")

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


def _axiom_errors(text: str) -> list[str]:
    matches = re.findall(r"depends on axioms:\s*\[([^\]]*)\]", text, re.IGNORECASE | re.DOTALL)
    if not matches and "does not depend on any axioms" not in text.lower():
        return ["no usable #print axioms output"]

    errors: list[str] = []
    for inner in matches:
        found = {p.strip().strip("`") for p in inner.split(",") if p.strip()}
        disallowed = found - ALLOWED_AXIOMS
        if disallowed:
            errors.append(f"disallowed axioms: {sorted(disallowed)}")
    return errors


def _docker_unavailable(text: str) -> bool:
    lowered = text.lower()
    return "error while fetching server api version" in lowered or "docker sdk required" in lowered


def _bisect_multiplex_failures(
    problems: list[Problem],
    image: str,
    *,
    initial_log_tail: str,
    witness: bool,
) -> list[str]:
    """Find failing template(s) without N separate workspaces (saves CI disk).

    When the all-in-one multiplex fails, binary-search which subset fails so we only run
    ``O(log n)`` multiplex builds, each in its own temp dir that is deleted immediately.
    """
    messages: list[str] = []
    bisect_step = itertools.count(1)

    def _bisect_log(phase: str, batch: list[Problem]) -> None:
        builders = [p.extra.get("builder_index") for p in batch]
        print(
            f"template bisect [{next(bisect_step)}] {phase}: "
            f"n_theorems={len(batch)} builders={builders}",
            file=sys.stderr,
            flush=True,
        )

    def isolate(batch: list[Problem]) -> None:
        if len(batch) == 1:
            _bisect_log("single-theorem workspace (lake build)", batch)
            tmp = Path(tempfile.mkdtemp(prefix="lemma-tpl-bisect-"))
            try:
                _materialize_multiplex(tmp, batch, witness=witness)
                code, out = _lake_build_only(tmp, image, witness=witness)
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
        _bisect_log("left half (lake build)", left)
        tmp_l = Path(tempfile.mkdtemp(prefix="lemma-tpl-bisect-"))
        try:
            _materialize_multiplex(tmp_l, left, witness=witness)
            code_l, out_l = _lake_build_only(tmp_l, image, witness=witness)
        finally:
            shutil.rmtree(tmp_l, ignore_errors=True)

        if code_l != 0:
            isolate(left)
            return

        _bisect_log("right half (lake build)", right)
        tmp_r = Path(tempfile.mkdtemp(prefix="lemma-tpl-bisect-"))
        try:
            _materialize_multiplex(tmp_r, right, witness=witness)
            code_r, out_r = _lake_build_only(tmp_r, image, witness=witness)
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


def _lake_build_only(work: Path, image: str, *, witness: bool) -> tuple[int, str]:
    """Return (exit_code, combined_output)."""
    inner = (
        "set -euo pipefail; "
        "lake exe cache get || true; "
        "lake build"
    )
    if witness:
        inner += "; lake env lean AxiomCheck.lean"
    try:
        import docker
        import docker.errors
    except ImportError as e:
        raise RuntimeError("docker SDK required") from e

    try:
        client = docker.from_env()
    except Exception as e:  # noqa: BLE001
        return 1, str(e)

    container = None
    try:
        container = client.containers.create(
            image,
            command=["bash", "-lc", inner],
            volumes={str(work.resolve()): {"bind": "/work", "mode": "rw"}},
            working_dir="/work",
            network_mode="bridge",
            user="0:0",
        )
        container.start()
        result = container.wait()
        raw_logs = container.logs(stdout=True, stderr=True)
        text = raw_logs.decode("utf-8", errors="replace") if isinstance(raw_logs, bytes) else str(raw_logs)
        status_code = int(result.get("StatusCode", 1))
        if status_code != 0:
            return status_code, text
        if witness:
            axiom_errors = _axiom_errors(text)
            if axiom_errors:
                return 1, text + "\nAXIOM CHECK FAILED:\n- " + "\n- ".join(axiom_errors)
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
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except Exception:
                pass


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _run_docker_multiplex(problems: list[Problem], image: str, *, witness: bool) -> int:
    label = "witness" if witness else "stub"
    tmp = Path(tempfile.mkdtemp(prefix=f"lemma-tpl-{label}-ci-"))
    try:
        _materialize_multiplex(tmp, problems, witness=witness)
        code, out = _lake_build_only(tmp, image, witness=witness)
        if code != 0:
            print(
                f"TEMPLATE BUILD FAILURE ({label} multiplex, {len(problems)} theorems) "
                f"exit={code}\n{out[-20000:]}",
                file=sys.stderr,
            )
            if _docker_unavailable(out):
                print("Docker is unavailable; skipping template bisection.", file=sys.stderr)
                return 1
            if not _env_truthy("CI_TEMPLATE_BISECT_ON_FAIL"):
                print(
                    "SKIP: set CI_TEMPLATE_BISECT_ON_FAIL=1 to run disk-heavy template bisection.",
                    file=sys.stderr,
                )
                return 1
            print(
                "Bisecting multiplex subsets (disk-friendly) to isolate failing builder(s)... "
                "Each step runs a full lake build and may take several minutes; progress lines follow.",
                file=sys.stderr,
                flush=True,
            )
            for msg in _bisect_multiplex_failures(
                problems,
                image,
                initial_log_tail=out,
                witness=witness,
            ):
                print(msg, "\n---\n", file=sys.stderr)
            return 1
        print(f"OK: {len(problems)} generated templates {label} lake build in one workspace ({image})")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    samples = _sample_all_builders()
    problems = [p for _, _, p in samples]
    print(f"OK: generated template metadata/witness gate covered {len(problems)} builders", flush=True)

    if os.environ.get("RUN_DOCKER_LEAN_TEMPLATES", "").strip() not in ("1", "true", "yes"):
        print("SKIP: set RUN_DOCKER_LEAN_TEMPLATES=1 to run stub+witness Lean checks", file=sys.stderr)
        return 0

    image = os.environ.get("LEAN_SANDBOX_IMAGE", "lemma/lean-sandbox:latest")

    if os.environ.get("CI_TEMPLATE_MULTIPLEX", "1").strip() not in ("0", "false", "no"):
        if _run_docker_multiplex(problems, image, witness=False) != 0:
            return 1
        return _run_docker_multiplex(problems, image, witness=True)

    # Slow / disk-heavy: one workspace per template (only when multiplex disabled).
    print(
        "WARN: CI_TEMPLATE_MULTIPLEX=0 — per-template Docker builds (high disk use).",
        file=sys.stderr,
    )
    from lemma.lean.workspace import materialize_workspace

    failures: list[str] = []
    for bi, seed, p in samples:
        stub = p.submission_stub()
        tmp = Path(tempfile.mkdtemp(prefix="lemma-tpl-ci-"))
        try:
            materialize_workspace(tmp, p, stub)
            code, out = _lake_build_only(tmp, image, witness=False)
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

    witness_failures: list[str] = []
    for bi, seed, p in samples:
        tmp = Path(tempfile.mkdtemp(prefix="lemma-tpl-witness-ci-"))
        try:
            materialize_workspace(tmp, p, generated_witness_submission_source(p))
            code, out = _lake_build_only(tmp, image, witness=True)
            if code != 0:
                witness_failures.append(
                    f"builder_index={bi} seed={seed} template_fn={p.extra.get('template_fn')} "
                    f"exit={code}\n{out[-12000:]}"
                )
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    if witness_failures:
        print("TEMPLATE WITNESS BUILD FAILURES:\n", file=sys.stderr)
        for f in witness_failures:
            print(f, "\n---\n", file=sys.stderr)
        return 1

    print(f"OK: {len(samples)} generated templates stub+witness lake build successfully ({image})")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as e:
        print(e, file=sys.stderr)
        raise SystemExit(1) from e
