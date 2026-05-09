"""Parse PutnamBench Lean 4 ``src/*.lean`` files (binder-heavy theorems)."""

from __future__ import annotations

import re
from pathlib import Path

from lemma.problems.base import SOLUTION_BRIDGE_THEOREM


def parse_putnam_file(path: Path) -> dict | None:
    """
    Build catalog row with ``challenge_full`` / ``solution_full`` / ``submission_stub``.

    Expects ``theorem ... :=\\nsorry`` style statements.
    """
    text = path.read_text(encoding="utf-8")
    if "sorry" not in text:
        return None

    lines = text.splitlines()
    opens: list[str] = []
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("import "):
            i += 1
            continue
        if s.startswith("open "):
            opens.append(lines[i])
            i += 1
            continue
        break

    body = "\n".join(lines[i:]).strip()
    m = re.search(r"theorem\s+(\w+)", body)
    if not m:
        return None
    name = m.group(1)

    preamble = "\n".join(opens)
    challenge_full = f"{preamble}\n\n{body}".strip() if preamble else body

    body_for_sol = re.sub(
        rf"^theorem\s+{re.escape(name)}\b",
        f"theorem {SOLUTION_BRIDGE_THEOREM}",
        body.strip(),
        count=1,
        flags=re.MULTILINE,
    )
    sol_body = re.sub(r":=\s*\n\s*sorry\s*$", f":= by\n  exact Submission.{name}", body_for_sol)
    solution_parts = ["import Submission"]
    if preamble:
        solution_parts.append(preamble)
    solution_parts.append(sol_body)
    solution_full = "\n\n".join(solution_parts)

    stub_body = re.sub(r":=\s*\n\s*sorry\s*$", ":= by\n  sorry", body.strip())
    stub_lines = ["import Mathlib"]
    if preamble:
        stub_lines.append(preamble)
    stub_lines.extend(["", "namespace Submission", "", stub_body, "", "end Submission"])
    submission_stub = "\n".join(stub_lines) + "\n"

    return {
        "theorem_name": name,
        "type_expr": f"PutnamBench {path.stem}",
        "challenge_full": challenge_full,
        "solution_full": solution_full,
        "submission_stub": submission_stub,
        "imports": [],
    }


def collect_putnam_src(src_dir: Path) -> list[dict]:
    rows: list[dict] = []
    if not src_dir.is_dir():
        return rows
    for p in sorted(src_dir.glob("*.lean")):
        row = parse_putnam_file(p)
        if row is None:
            continue
        row["id"] = f"putnam/{p.stem}"
        row["split"] = "putnam"
        rows.append(row)
    return rows
