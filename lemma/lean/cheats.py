"""Heuristic scans for disallowed tokens in miner-owned Lean source."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Trivial cheats and dangerous primitives
_FORBIDDEN = re.compile(
    r"\b(sorry|admit|native_decide|unsafe|unsafeCast|reduceBool)\b",
    re.IGNORECASE,
)
# User-declared axioms (not the word 'axioms' from #print)
_AXIOM_DECL = re.compile(r"^\s*axiom\s+\w+", re.MULTILINE)


@dataclass(frozen=True)
class CheatScan:
    ok: bool
    reason: str | None = None


def scan_submission_for_cheats(source: str) -> CheatScan:
    """Return ok=False if obvious cheat tokens appear in ``Submission.lean``."""
    if _FORBIDDEN.search(source):
        return CheatScan(False, "forbidden_token")
    if _AXIOM_DECL.search(source):
        return CheatScan(False, "user_axiom")
    return CheatScan(True, None)


def cheat_scan_stderr_tail(scan: CheatScan, *, max_len: int = 8000) -> str:
    """Human-readable tail for ``VerifyResult`` when ``scan.ok`` is false."""
    if scan.ok:
        return ""
    tail = scan.reason or ""
    if tail == "forbidden_token":
        tail += (
            " — remove `sorry`, `admit`, `unsafe`, … from Submission.lean (completed proof only). "
            "`lemma/lean/template/Submission.lean` is a stub and will always fail this check."
        )
    elif tail == "user_axiom":
        tail += " — do not declare new `axiom`s in Submission.lean."
    return tail[:max_len]


ALLOWED_AXIOMS = frozenset({"propext", "Quot.sound", "Classical.choice"})


def parse_axioms_from_lean_output(text: str) -> set[str] | None:
    """
    Parse ``#print axioms`` line from ``lake env lean AxiomCheck.lean`` output.

    Expected shape contains ``depends on axioms: [a, b, c]`` (Lean 4 pretty-print).
    Pure ``rfl`` / definitional proofs may print ``does not depend on any axioms`` instead.
    """
    low = text.lower()
    if "does not depend on any axioms" in low:
        return set()
    m = re.search(r"depends on axioms:\s*\[([^\]]*)\]", text, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    inner = m.group(1)
    parts = [p.strip().strip("`") for p in inner.split(",") if p.strip()]
    return set(parts)


def lean_driver_failed(lean_output: str) -> bool:
    """True if Lean/lake failed before a usable ``#print axioms`` line."""
    t = lean_output.lower()
    return (
        "error (" in t
        or "unknown identifier" in t
        or "unknown constant" in t
        or "invalid field" in t
        or "error:" in t
        or "build failed" in t
        or "failed to build" in t
    )


def lake_build_environment_failed(lean_output: str) -> bool:
    """True when lake/git failed for network or tooling — not a rejected proof or axiom issue."""
    t = lean_output.lower()
    return (
        "could not resolve host" in t
        or "couldn't resolve host" in t
        or ("git" in t and "exit code 128" in t)
        or "network is unreachable" in t
        or "failed to download" in t
        or "tls handshake" in t
    )


def axiom_scan_ok(lean_output: str) -> tuple[bool, set[str] | None]:
    """True iff parsed axiom set is a subset of ALLOWED_AXIOMS (empty allowed)."""
    found = parse_axioms_from_lean_output(lean_output)
    if found is None:
        return False, None
    if not found.issubset(ALLOWED_AXIOMS):
        return False, found
    return True, found
