"""Sample ``theorem … : … := by sorry`` stubs from a mathlib4 checkout."""

from __future__ import annotations

from pathlib import Path

from tools.catalog.minif2f_parse import THEOREM_LINE


def collect_mathlib_theorems(
    mathlib_root: Path,
    *,
    max_files: int = 400,
    max_theorems: int = 500,
    glob_pattern: str = "**/*.lean",
) -> list[dict]:
    """Walk ``Mathlib/`` (relative to repo root) for simple one-line sorry stubs."""
    mathlib_dir = mathlib_root / "Mathlib"
    if not mathlib_dir.is_dir():
        return []

    rows: list[dict] = []
    n_files = 0
    for path in sorted(mathlib_dir.glob(glob_pattern)):
        if n_files >= max_files:
            break
        if "/test/" in str(path) or ".test." in path.name:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        n_files += 1
        rel = path.relative_to(mathlib_root)
        for m in THEOREM_LINE.finditer(text):
            name, typ = m.group(1), m.group(2).strip()
            rid = f"mathlib/{rel.as_posix().replace('/', '_')}/{name}"
            rows.append(
                {
                    "id": rid,
                    "split": "mathlib",
                    "topic": "mathlib/sample",
                    "theorem_name": name,
                    "type_expr": typ[:4000] + ("..." if len(typ) > 4000 else ""),
                }
            )
            if len(rows) >= max_theorems:
                return rows
    return rows
