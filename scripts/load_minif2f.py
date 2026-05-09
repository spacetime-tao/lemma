#!/usr/bin/env python3
"""
Clone a miniF2F Lean 4 repo and emit ``lemma/problems/minif2f_frozen.json``.

Prefer ``scripts/build_lemma_catalog.py`` when merging multiple upstream datasets.

Usage:
  python scripts/load_minif2f.py --out lemma/problems/minif2f_frozen.json

Requires: git, network. Parses ``MiniF2F/Test`` and ``MiniF2F/Valid`` for both single-line
and multi-line ``theorem … := by sorry`` stubs.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from lemma.catalog.constants import DEFAULT_LEAN_TOOLCHAIN, DEFAULT_MATHLIB_REV
from tools.catalog.minif2f_parse import collect_minif2f_layout


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="https://github.com/yangky11/miniF2F-lean4.git")
    ap.add_argument("--ref", default="main")
    ap.add_argument("--out", type=Path, default=Path("lemma/problems/minif2f_frozen.json"))
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as td:
        clone = Path(td) / "miniF2F-lean4"
        subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", args.ref, args.repo, str(clone)],
            check=True,
        )
        rows = collect_minif2f_layout(clone)
        if not rows:
            print("No theorems parsed; check repo layout / regex.", file=sys.stderr)
            return 1
        for r in rows:
            r.setdefault("lean_toolchain", DEFAULT_LEAN_TOOLCHAIN)
            r.setdefault("mathlib_rev", DEFAULT_MATHLIB_REV)
            if "imports" not in r:
                r["imports"] = ["Mathlib"]
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {len(rows)} problems to {args.out}")

        manifest = {
            "upstream_repo": args.repo,
            "upstream_ref": args.ref,
            "problem_count": len(rows),
            "generated_at": datetime.now(UTC).isoformat(),
            "notes": "Pin Lean/mathlib in compose/lean.Dockerfile to match rows.",
        }
        manifest_path = args.out.parent / "catalog_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote manifest to {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
