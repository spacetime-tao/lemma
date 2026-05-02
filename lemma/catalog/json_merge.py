"""Load supplemental catalog fragments from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_REQUIRED = frozenset({"id", "theorem_name", "type_expr", "split", "lean_toolchain", "mathlib_rev"})


def load_catalog_json(path: Path) -> list[dict[str, Any]]:
    """Load a JSON array of catalog rows; validate required scalar keys."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: expected JSON array")
    out: list[dict[str, Any]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            raise ValueError(f"{path}: row {i} is not an object")
        missing = _REQUIRED - row.keys()
        if missing:
            raise ValueError(f"{path}: row {i} missing keys {sorted(missing)}")
        out.append(row)
    return out
