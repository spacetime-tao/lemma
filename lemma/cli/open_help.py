"""Open paths with the OS default application."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def open_paths_in_os(paths: list[Path]) -> Path | None:
    """Open the first existing file; return that path, or None."""
    for p in paths:
        if not p.is_file():
            continue
        sp = str(p.resolve())
        if sys.platform == "darwin":
            subprocess.run(["open", sp], check=False)
            return p
        if sys.platform.startswith("linux"):
            subprocess.run(["xdg-open", sp], check=False)
            return p
        if sys.platform == "win32":
            os.startfile(sp)  # type: ignore[attr-defined]
            return p
    return None
