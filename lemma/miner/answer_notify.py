"""Optional user-visible ping when a miner forward is about to return (after building the synapse)."""

from __future__ import annotations

import subprocess
import sys
import threading

from loguru import logger


def _applescript_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def notify_miner_answer_sent(*, theorem_id: str, solve_s: float, local_lean: str) -> None:
    """Bell + optional macOS banner; never raises."""
    try:
        sys.stderr.write("\a")
        sys.stderr.flush()
    except Exception:
        pass
    if sys.platform != "darwin":
        return
    one_line = f"{theorem_id} · {solve_s:.1f}s · local_lean={local_lean}"
    if len(one_line) > 180:
        one_line = one_line[:177] + "…"
    body = _applescript_escape(one_line)
    title = _applescript_escape("Lemma miner — answer sent")
    script = f'display notification "{body}" with title "{title}"'
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=8,
            check=False,
        )
        if r.returncode != 0:
            err = (r.stderr or b"").decode("utf-8", errors="replace").strip()
            logger.warning(
                "miner answer macOS notification failed (returncode={}): {} — "
                "allow notifications for this terminal in System Settings → Notifications",
                r.returncode,
                (err or "(no stderr)")[:300],
            )
    except Exception as e:
        logger.warning("miner answer macOS notification error: {}", e)


def notify_miner_answer_sent_async(*, theorem_id: str, solve_s: float, local_lean: str) -> None:
    """Fire-and-forget so the axon reply path is not blocked by osascript."""
    t = threading.Thread(
        target=notify_miner_answer_sent,
        kwargs={"theorem_id": theorem_id, "solve_s": solve_s, "local_lean": local_lean},
        daemon=True,
    )
    t.start()
