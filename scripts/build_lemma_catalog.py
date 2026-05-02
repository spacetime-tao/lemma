#!/usr/bin/env python3
"""
Build a merged ``minif2f_frozen.json`` from multiple upstream Lean 4 sources.

Sources (see ``docs/CATALOG_SOURCES.md``):
  yangky          — yangky11/miniF2F-lean4 (competition-style)
  dm              — google-deepmind/miniF2F (Lean 4 fork)
  putnam          — trishullab/PutnamBench ``lean4/src``
  formalmath_lite — Hugging Face ``SphereLab/FormalMATH-Lite`` (needs ``--extra catalog`` / ``datasets``)
  formalmath_all  — Hugging Face ``SphereLab/FormalMATH-All``
  mathlib         — sample ``theorem … : … := by sorry`` from a local mathlib4 checkout

Also:

  ``--merge-json PATH`` — merge extra Lemma-format JSON arrays (repeatable).
  ``--extra-repo URL REF PREFIX`` — clone any Lean repo; if it has ``MiniF2F/{Test,Valid}`` use that layout,
  otherwise scan up to ``--extra-repo-max-files`` ``*.lean`` files for sorry-stubs (repeatable).

Examples::

  uv sync --extra catalog   # optional: FormalMATH import
  python scripts/build_lemma_catalog.py --out lemma/problems/minif2f_frozen.json \\
      --sources yangky,dm,putnam

  python scripts/build_lemma_catalog.py --sources formalmath_lite --formalmath-max-rows 2000

  python scripts/build_lemma_catalog.py --sources mathlib --mathlib-root ~/mathlib4

openai/miniF2F is Lean 3 only; use yangky or DeepMind for Lean 4.
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
from lemma.catalog.minif2f_parse import collect_minif2f_layout


def _clone(repo: str, ref: str, dest: Path) -> None:
    subprocess.run(
        ["git", "clone", "--depth", "1", "--branch", ref, repo, str(dest)],
        check=True,
    )


def _pin_standard(rows: list[dict], toolchain: str, mathlib_rev: str) -> None:
    for r in rows:
        r.setdefault("lean_toolchain", toolchain)
        r.setdefault("mathlib_rev", mathlib_rev)
        if "imports" not in r:
            r["imports"] = ["Mathlib"]


def _tag_topic(rows: list[dict], topic: str) -> None:
    """Set ``topic`` for dataset stratification (preserves explicit tags in merged rows)."""
    for r in rows:
        r.setdefault("topic", topic)


def _dedupe(rows: list[dict]) -> list[dict]:
    by_id: dict[str, dict] = {}
    for r in rows:
        by_id[str(r["id"])] = r
    return [by_id[k] for k in sorted(by_id.keys())]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--out",
        type=Path,
        default=Path("lemma/problems/minif2f_frozen.json"),
        help="Output JSON array path",
    )
    ap.add_argument(
        "--sources",
        type=str,
        default="yangky,dm,putnam",
        help="Comma-separated source keys (see module docstring)",
    )
    ap.add_argument("--toolchain", default=DEFAULT_LEAN_TOOLCHAIN)
    ap.add_argument("--mathlib-rev", default=DEFAULT_MATHLIB_REV)
    ap.add_argument("--yangky-repo", default="https://github.com/yangky11/miniF2F-lean4.git")
    ap.add_argument("--yangky-ref", default="main")
    ap.add_argument("--dm-repo", default="https://github.com/google-deepmind/miniF2F.git")
    ap.add_argument("--dm-ref", default="main")
    ap.add_argument("--putnam-repo", default="https://github.com/trishullab/PutnamBench.git")
    ap.add_argument("--putnam-ref", default="main")
    ap.add_argument("--formalmath-max-rows", type=int, default=0, help="0 = skip or include all streamed")
    ap.add_argument(
        "--mathlib-root",
        type=Path,
        default=None,
        help="Path to mathlib4 repo root (contains Mathlib/)",
    )
    ap.add_argument("--mathlib-max-files", type=int, default=400)
    ap.add_argument("--mathlib-max-theorems", type=int, default=500)
    ap.add_argument(
        "--merge-json",
        action="append",
        default=[],
        type=Path,
        help="Merge Lemma-format JSON catalog fragments (repeatable)",
    )
    ap.add_argument(
        "--extra-repo",
        action="append",
        nargs=3,
        metavar=("URL", "REF", "PREFIX"),
        help="Clone URL at REF and ingest as PREFIX (MiniF2F layout if present, else loose scan; repeatable)",
    )
    ap.add_argument("--extra-repo-max-files", type=int, default=800)
    args = ap.parse_args()

    keys = [k.strip() for k in args.sources.split(",") if k.strip()]
    all_rows: list[dict] = []
    extra_repos = args.extra_repo or []

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)

        if "yangky" in keys:
            root = base / "miniF2F-lean4"
            _clone(args.yangky_repo, args.yangky_ref, root)
            rows = collect_minif2f_layout(root)
            for r in rows:
                r["id"] = f"yk/{r['id']}"
                r["split"] = f"yk_{r['split']}"
            _pin_standard(rows, args.toolchain, args.mathlib_rev)
            _tag_topic(rows, "miniF2F/yangky")
            all_rows.extend(rows)
            print(f"yangky: {len(rows)} problems")

        if "dm" in keys:
            root = base / "miniF2F-dm"
            _clone(args.dm_repo, args.dm_ref, root)
            rows = collect_minif2f_layout(root)
            for r in rows:
                r["id"] = f"dm/{r['id']}"
                r["split"] = f"dm_{r['split']}"
            _pin_standard(rows, args.toolchain, args.mathlib_rev)
            _tag_topic(rows, "miniF2F/deepmind")
            all_rows.extend(rows)
            print(f"dm: {len(rows)} problems")

        if "putnam" in keys:
            from lemma.catalog.putnam import collect_putnam_src

            root = base / "PutnamBench"
            _clone(args.putnam_repo, args.putnam_ref, root)
            lean4 = root / "lean4"
            lt_path = lean4 / "lean-toolchain"
            tc = lt_path.read_text(encoding="utf-8").strip() if lt_path.is_file() else args.toolchain
            rows = collect_putnam_src(lean4 / "src")
            for r in rows:
                r["lean_toolchain"] = tc
                r["mathlib_rev"] = args.mathlib_rev
            _tag_topic(rows, "putnam")
            all_rows.extend(rows)
            print(f"putnam: {len(rows)} problems")

        fm_datasets = {
            "formalmath_lite": "SphereLab/FormalMATH-Lite",
            "formalmath_all": "SphereLab/FormalMATH-All",
        }
        for fm_key, hf_id in fm_datasets.items():
            if fm_key not in keys:
                continue
            try:
                from datasets import load_dataset
            except ImportError:
                print(
                    "FormalMATH requires the `datasets` package: uv sync --extra catalog",
                    file=sys.stderr,
                )
                return 1
            from lemma.catalog.formalmath import row_from_hf_record

            ds = load_dataset(hf_id, split="train", streaming=True)
            rows = []
            skipped = 0
            want = args.formalmath_max_rows or 10**12
            safety = max(want + 50_000, 100_000)
            for i, rec in enumerate(ds):
                if len(rows) >= want:
                    break
                if i >= safety:
                    print(f"warning: {fm_key} stopped at safety iteration cap {safety}", file=sys.stderr)
                    break
                try:
                    rows.append(row_from_hf_record(rec, i, split_tag=fm_key))
                except ValueError:
                    skipped += 1
                    continue
            for r in rows:
                r.setdefault("lean_toolchain", args.toolchain)
                r.setdefault("mathlib_rev", args.mathlib_rev)
            _tag_topic(rows, fm_key.replace("formalmath_", "formalmath/", 1))
            all_rows.extend(rows)
            print(f"{fm_key}: {len(rows)} problems ({skipped} HF rows skipped)")

        if "mathlib" in keys:
            if not args.mathlib_root or not args.mathlib_root.is_dir():
                print("--mathlib-root required for mathlib source", file=sys.stderr)
                return 1
            from lemma.catalog.mathlib_sample import collect_mathlib_theorems

            rows = collect_mathlib_theorems(
                args.mathlib_root,
                max_files=args.mathlib_max_files,
                max_theorems=args.mathlib_max_theorems,
            )
            _pin_standard(rows, args.toolchain, args.mathlib_rev)
            _tag_topic(rows, "mathlib/sample")
            all_rows.extend(rows)
            print(f"mathlib: {len(rows)} problems")

        for url, ref, prefix in extra_repos:
            dest = base / prefix.replace("/", "_")
            _clone(url, ref, dest)
            if (dest / "MiniF2F").is_dir():
                rows = collect_minif2f_layout(dest)
                for r in rows:
                    r["id"] = f"{prefix}/{r['id']}"
                    r["split"] = f"{prefix}_{r['split']}"
                _pin_standard(rows, args.toolchain, args.mathlib_rev)
            else:
                from lemma.catalog.loose_scan import collect_loose_lean_repo

                rows = collect_loose_lean_repo(
                    dest,
                    prefix,
                    max_files=args.extra_repo_max_files,
                )
                _pin_standard(rows, args.toolchain, args.mathlib_rev)
            _tag_topic(rows, f"extra/{prefix}")
            all_rows.extend(rows)
            print(f"extra-repo {prefix}: {len(rows)} problems")

    for mj in args.merge_json:
        from lemma.catalog.json_merge import load_catalog_json

        rows = load_catalog_json(mj)
        _pin_standard(rows, args.toolchain, args.mathlib_rev)
        _tag_topic(rows, "catalog/merge")
        all_rows.extend(rows)
        print(f"merge-json {mj}: {len(rows)} problems")

    merged = _dedupe(all_rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(merged)} unique problems to {args.out}")

    manifest = {
        "sources": keys,
        "merge_json": [str(p) for p in args.merge_json],
        "extra_repos": [{"url": u, "ref": r, "prefix": p} for u, r, p in extra_repos],
        "problem_count": len(merged),
        "generated_at": datetime.now(UTC).isoformat(),
        "lean_toolchain_default": args.toolchain,
        "mathlib_rev_default": args.mathlib_rev,
        "notes": "See docs/CATALOG_SOURCES.md. Align compose/lean.Dockerfile with toolchain pins.",
    }
    man_path = args.out.parent / "catalog_manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {man_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
