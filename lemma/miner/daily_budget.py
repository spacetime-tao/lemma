"""Optional cap on miner forwards per UTC day (saves inference spend)."""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path

_STATE_VERSION = 1
_lock = threading.Lock()


def _utc_day() -> str:
    return datetime.now(UTC).date().isoformat()


def _state_path() -> Path:
    return Path.home() / ".lemma" / "miner_daily_forwards.json"


def allow_daily_forward(max_per_day: int, *, state_path: Path | None = None) -> bool:
    """
    Return True if this forward should run the prover.

    ``max_per_day <= 0`` means unlimited. Counter resets automatically each UTC day.
    Persists under ``~/.lemma/miner_daily_forwards.json`` so restarts don't reset the budget.
    """
    if max_per_day <= 0:
        return True

    with _lock:
        return _allow_daily_forward_locked(max_per_day, state_path)


def _allow_daily_forward_locked(max_per_day: int, state_path: Path | None) -> bool:
    path = state_path or _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    day = _utc_day()

    data: dict[str, object] = {}
    if path.exists():
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except (json.JSONDecodeError, OSError):
            data = {}

    if data.get("version") != _STATE_VERSION:
        data = {"version": _STATE_VERSION}

    stored_day = data.get("day")
    count = int(data.get("count") or 0)
    if stored_day != day:
        stored_day = day
        count = 0

    if count >= max_per_day:
        return False

    count += 1
    out = {"version": _STATE_VERSION, "day": stored_day, "count": count}
    path.write_text(json.dumps(out), encoding="utf-8")
    return True
