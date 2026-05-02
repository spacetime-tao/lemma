"""Optional post-verify hook (e.g. leanprover/comparator or custom scripts).

Disabled unless ``LEMMA_COMPARATOR_ENABLED=1`` and ``LEMMA_COMPARATOR_CMD`` is set.
Use for experimentation; production comparator wiring is operator-specific.
"""

from __future__ import annotations

import os
import shlex
import subprocess
from pathlib import Path

from pydantic import BaseModel


class ComparatorHookResult(BaseModel):
    ok: bool
    stderr_tail: str = ""


def run_comparator_hook(work: Path, *, timeout_s: float) -> ComparatorHookResult | None:
    """Return ``None`` if hook skipped; otherwise pass/fail + stderr snippet."""
    if os.environ.get("LEMMA_COMPARATOR_ENABLED", "").strip().lower() not in ("1", "true", "yes"):
        return None
    cmd_raw = os.environ.get("LEMMA_COMPARATOR_CMD", "").strip()
    if not cmd_raw:
        return None
    try:
        argv = shlex.split(cmd_raw)
    except ValueError as e:
        return ComparatorHookResult(ok=False, stderr_tail=f"LEMMA_COMPARATOR_CMD parse error: {e}")
    try:
        r = subprocess.run(
            argv,
            cwd=work,
            capture_output=True,
            text=True,
            timeout=min(timeout_s, float(os.environ.get("LEMMA_COMPARATOR_TIMEOUT_S", "120"))),
        )
    except subprocess.TimeoutExpired:
        return ComparatorHookResult(ok=False, stderr_tail="comparator hook timeout")
    except OSError as e:
        return ComparatorHookResult(ok=False, stderr_tail=str(e))
    tail = ((r.stderr or "") + "\n" + (r.stdout or ""))[-8000:]
    if r.returncode != 0:
        return ComparatorHookResult(ok=False, stderr_tail=tail)
    return ComparatorHookResult(ok=True, stderr_tail=tail[-2000:])


def hook_failure_reason(result: ComparatorHookResult | None) -> str | None:
    """Return sandbox failure reason if hook ran and failed."""
    if result is None or result.ok:
        return None
    return "comparator_rejected"
