from __future__ import annotations

import subprocess
from pathlib import Path


def test_dashboard_refresh_script_has_valid_shell_and_lock() -> None:
    script = Path("deploy/scripts/lemma-refresh-public-dashboard")

    subprocess.run(["bash", "-n", str(script)], check=True)

    text = script.read_text(encoding="utf-8")
    assert "flock -n 9" in text
    assert "public dashboard refresh already running" in text
