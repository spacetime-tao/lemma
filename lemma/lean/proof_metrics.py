"""Compare-only Lean-backed proof measurements."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

PROOF_METRICS_SOURCE = "print_decl_pp_all_v1"
PROOF_METRICS_MARKER = "LEMMA_PROOF_METRICS"
PROOF_METRICS_FILE = "ProofMetrics.lean"

_METRICS_LINE = re.compile(
    rf"^{PROOF_METRICS_MARKER}\s+"
    rf"(?P<source>\S+)\s+bytes=(?P<bytes>\d+)\s+lines=(?P<lines>\d+)\s+exit=(?P<exit>\d+)\s*$",
    re.MULTILINE,
)


class LeanProofMetrics(BaseModel):
    """Experimental metrics for comparison only; never part of live scoring."""

    source: Literal["print_decl_pp_all_v1"] = PROOF_METRICS_SOURCE
    proof_declaration_bytes: int = Field(ge=0)
    proof_declaration_lines: int = Field(ge=0)
    probe_exit_code: int = Field(ge=0)


def proof_metrics_probe_source(theorem_name: str) -> str:
    """Lean probe that prints the verified theorem declaration after `Submission` builds."""
    return f"""import Submission
set_option pp.all true
#print Submission.{theorem_name}
"""


def write_proof_metrics_probe(work: Path, theorem_name: str) -> None:
    (work / PROOF_METRICS_FILE).write_text(proof_metrics_probe_source(theorem_name), encoding="utf-8")


def proof_metrics_from_probe_output(text: str, *, exit_code: int) -> LeanProofMetrics:
    raw = text or ""
    return LeanProofMetrics(
        proof_declaration_bytes=len(raw.encode("utf-8")),
        proof_declaration_lines=len(raw.splitlines()),
        probe_exit_code=max(0, int(exit_code)),
    )


def parse_proof_metrics_line(text: str) -> LeanProofMetrics | None:
    matches = list(_METRICS_LINE.finditer(text or ""))
    if not matches:
        return None
    m = matches[-1]
    if m.group("source") != PROOF_METRICS_SOURCE:
        return None
    return LeanProofMetrics(
        proof_declaration_bytes=int(m.group("bytes")),
        proof_declaration_lines=int(m.group("lines")),
        probe_exit_code=int(m.group("exit")),
    )


def collect_host_proof_metrics(
    work: Path,
    *,
    timeout_s: float,
    env: dict[str, str],
) -> LeanProofMetrics | None:
    """Run the compare-only probe in an already verified host workspace."""
    probe = work / PROOF_METRICS_FILE
    if not probe.is_file():
        return None
    try:
        r = subprocess.run(
            ["lake", "env", "lean", str(probe)],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return proof_metrics_from_probe_output("", exit_code=124)
    except OSError:
        return proof_metrics_from_probe_output("", exit_code=127)
    return proof_metrics_from_probe_output((r.stdout or "") + (r.stderr or ""), exit_code=r.returncode)


def docker_proof_metrics_shell_fragment() -> str:
    """Non-failing shell fragment that emits one parseable metrics line."""
    return (
        f"if [ -f {PROOF_METRICS_FILE} ]; then "
        f"set +e; lake env lean {PROOF_METRICS_FILE} > ProofMetrics.out 2>&1; rc=$?; "
        "bytes=$(wc -c < ProofMetrics.out 2>/dev/null | tr -d ' '); "
        "lines=$(awk 'END { print NR }' ProofMetrics.out 2>/dev/null); "
        "bytes=${bytes:-0}; lines=${lines:-0}; "
        f"printf '\\n{PROOF_METRICS_MARKER} {PROOF_METRICS_SOURCE} "
        "bytes=%s lines=%s exit=%s\\n' \"$bytes\" \"$lines\" \"$rc\"; set -e; "
        "fi"
    )
