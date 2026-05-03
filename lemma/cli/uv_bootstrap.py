"""Optional ``uv run`` re-exec so bare ``lemma`` matches ``uv run lemma`` in dev trees."""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _lemma_repo_root(start: Path) -> Path | None:
    """Find a checkout whose layout matches this repo (has ``lemma/lean/sandbox.py``)."""
    cur = start.resolve()
    for _ in range(12):
        if (
            (cur / "pyproject.toml").is_file()
            and (cur / "lemma" / "lean" / "sandbox.py").is_file()
        ):
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _venv_python(repo: Path) -> Path | None:
    if sys.platform == "win32":
        p = repo / ".venv" / "Scripts" / "python.exe"
    else:
        p = repo / ".venv" / "bin" / "python"
    return p if p.is_file() else None


def maybe_reexec_under_uv() -> None:
    """If we're not running under this repo's ``.venv`` Python, re-exec via ``uv run lemma …``.

    Skipped when ``LEMMA_NO_UV_REEXEC`` is set (CI / explicit opt-out), when ``LEMMA_UV_REEXEC``
    already ran once, when no ``uv`` on PATH, or when not launched from a dev checkout / no ``.venv``.
    """
    if os.environ.get("LEMMA_NO_UV_REEXEC", "").strip() in ("1", "true", "yes"):
        return
    if os.environ.get("LEMMA_UV_REEXEC", "").strip() == "1":
        return

    here = Path(__file__).resolve()
    repo = _lemma_repo_root(here.parent)
    if repo is None:
        return

    target = _venv_python(repo)
    if target is None:
        return

    try:
        if Path(sys.executable).resolve() == target.resolve():
            return
    except OSError:
        return

    uv = shutil.which("uv")
    if not uv:
        return

    os.environ["LEMMA_UV_REEXEC"] = "1"
    argv = [uv, "run", "--project", str(repo), "lemma", *sys.argv[1:]]
    os.execvp(uv, argv)
