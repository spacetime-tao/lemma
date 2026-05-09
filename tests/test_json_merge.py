"""Catalog JSON merge validation."""

import json
from pathlib import Path

import pytest
from tools.catalog.json_merge import load_catalog_json


def test_load_catalog_json_ok(tmp_path: Path) -> None:
    row = {
        "id": "x/y",
        "theorem_name": "t",
        "type_expr": "Nat",
        "split": "test",
        "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
        "mathlib_rev": "5450b53e5ddc",
    }
    p = tmp_path / "frag.json"
    p.write_text(json.dumps([row]), encoding="utf-8")
    assert len(load_catalog_json(p)) == 1


def test_load_catalog_json_missing_key(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([{"id": "only"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        load_catalog_json(p)
