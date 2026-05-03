"""Resolve `.venv` paths for operator shells (activate script)."""

from __future__ import annotations

from pathlib import Path


def venv_activate_script() -> Path | None:
    """Return ``.venv/bin/activate`` if we can find it (cwd first, then package layout)."""
    cwd = Path.cwd() / ".venv" / "bin" / "activate"
    if cwd.is_file():
        return cwd.resolve()
    # Editable dev layout: repo/lemma/cli/… → parents[2] = repo root
    here = Path(__file__).resolve()
    for depth in (2, 3):
        if len(here.parents) > depth:
            cand = here.parents[depth] / ".venv" / "bin" / "activate"
            if cand.is_file():
                return cand.resolve()
    return None
