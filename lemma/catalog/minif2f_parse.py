"""Parse miniF2F-style Lean trees (single-line or multi-line ``sorry`` stubs)."""

from __future__ import annotations

import re
from pathlib import Path

# Single-line (Lean 4)
THEOREM_LINE = re.compile(
    r"^\s*theorem\s+(\w+)\s*:\s*(.+?)\s*:=\s*by\s+sorry\s*$",
    re.MULTILINE,
)
# Multi-line: theorem header … := by … sorry (allows binders across lines)
THEOREM_BLOCK = re.compile(
    r"(?ms)^(\s*)theorem\s+(\w+)\s*(.*?)\s*:=\s*by\s+sorry\s*$",
)


def parse_minif2f_file(path: Path, split: str) -> list[dict]:
    """Extract theorem stubs from one ``.lean`` file."""
    text = path.read_text(encoding="utf-8")
    rows: list[dict] = []
    stem = path.stem

    for m in THEOREM_LINE.finditer(text):
        name, typ = m.group(1), m.group(2).strip()
        pid = f"{split}/{stem}/{name}"
        rows.append(_row(pid, split, name, typ))

    seen = {r["theorem_name"] for r in rows}
    for m in THEOREM_BLOCK.finditer(text):
        name = m.group(2)
        if name in seen:
            continue
        mid = m.group(3).strip()
        typ = " ".join(mid.split())
        if len(typ) > 8000:
            typ = typ[:7997] + "..."
        pid = f"{split}/{stem}/{name}"
        rows.append(_row(pid, split, name, typ))
        seen.add(name)

    return rows


def _row(pid: str, split: str, name: str, typ: str) -> dict:
    return {
        "id": pid,
        "split": split,
        "theorem_name": name,
        "type_expr": typ,
    }


def collect_minif2f_layout(root: Path, split_test: str = "test", split_valid: str = "valid") -> list[dict]:
    """Collect from ``MiniF2F/Test`` and ``MiniF2F/Valid`` (yangky / DeepMind layout).

    Supports directory layout (``MiniF2F/Test/*.lean``) or single-file layout
    (``MiniF2F/Test.lean``, ``MiniF2F/Valid.lean`` as used by google-deepmind/miniF2F).
    """
    rows: list[dict] = []
    mini = root / "MiniF2F"
    if not mini.is_dir():
        return rows
    test_dir = mini / "Test"
    valid_dir = mini / "Valid"
    test_file = mini / "Test.lean"
    valid_file = mini / "Valid.lean"

    if test_dir.is_dir():
        for p in sorted(test_dir.glob("*.lean")):
            rows.extend(parse_minif2f_file(p, split_test))
    elif test_file.is_file():
        rows.extend(parse_minif2f_file(test_file, split_test))

    if valid_dir.is_dir():
        for p in sorted(valid_dir.glob("*.lean")):
            rows.extend(parse_minif2f_file(p, split_valid))
    elif valid_file.is_file():
        rows.extend(parse_minif2f_file(valid_file, split_valid))

    return rows
