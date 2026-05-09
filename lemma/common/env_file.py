"""Merge key=value pairs into a `.env` file without parsing multi-line values."""

from __future__ import annotations

from pathlib import Path


def _parse_key(line: str) -> str | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None
    key = stripped.split("=", 1)[0].strip()
    if key.startswith("export "):
        key = key[7:].strip()
    return key or None


def _quote_value(val: str) -> str:
    esc = val.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{esc}"'


def merge_dotenv(path: Path, updates: dict[str, str]) -> None:
    """Remove existing assignments for keys in ``updates``, append new lines."""
    lines_out: list[str] = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key = _parse_key(line)
            if key is not None and key in updates:
                continue
            lines_out.append(line)
    else:
        parent = path.parent
        example = parent / ".env.example"
        if example.exists():
            lines_out.extend(example.read_text(encoding="utf-8").splitlines())

    if lines_out and lines_out[-1].strip():
        lines_out.append("")
    lines_out.append("# lemma-cli configure")
    for k, v in updates.items():
        lines_out.append(f"{k}={_quote_value(v)}")
    path.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
