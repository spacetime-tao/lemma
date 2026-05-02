"""Scan arbitrary Lean repo trees for miniF2F-style ``theorem … := by sorry`` stubs."""

from __future__ import annotations

from pathlib import Path

from lemma.catalog.minif2f_parse import parse_minif2f_file


def _skip_path(path: Path) -> bool:
    parts = set(path.parts)
    return ".lake" in parts or "build" in parts or ".git" in parts


def collect_loose_lean_repo(
    root: Path,
    id_prefix: str,
    *,
    max_files: int = 800,
    split_label: str = "extra",
) -> list[dict]:
    """
    Walk ``root`` for ``*.lean`` files and extract theorems via the same regexes as miniF2F.

    IDs look like ``{prefix}/{relpath_with_underscores}/{theorem_name}``.
    """
    rows: list[dict] = []
    n_read = 0
    for path in sorted(root.rglob("*.lean")):
        if _skip_path(path):
            continue
        if n_read >= max_files:
            break
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "theorem" not in text or "sorry" not in text:
            continue
        n_read += 1
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path.name
        rel_str = rel.as_posix().replace("/", "_").replace(".lean", "")
        chunk = parse_minif2f_file(path, split_label)
        for r in chunk:
            name = r["theorem_name"]
            r["id"] = f"{id_prefix}/{rel_str}/{name}"
            r["split"] = f"{split_label}_{id_prefix}"
        rows.extend(chunk)
    return rows
