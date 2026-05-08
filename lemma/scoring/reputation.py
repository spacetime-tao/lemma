"""Per-UID EMA reputation state persisted on disk (validator-local)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lemma.scoring.pareto import ScoredEntry


@dataclass
class ReputationStore:
    """EMA scores per miner UID (validator process)."""

    ema_by_uid: dict[int, float]
    version: int = 1

    def to_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "ema_by_uid": {str(k): v for k, v in sorted(self.ema_by_uid.items())},
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ReputationStore:
        raw = data.get("ema_by_uid") or {}
        ema: dict[int, float] = {}
        for k, v in raw.items():
            ema[int(k)] = float(v)
        ver = int(data.get("version", 1))
        return cls(ema_by_uid=ema, version=ver)


def default_reputation_path() -> Path:
    return Path.home() / ".lemma" / "validator_reputation.json"


def load_reputation(path: Path | None) -> ReputationStore:
    p = path or default_reputation_path()
    if not p.is_file():
        return ReputationStore(ema_by_uid={})
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return ReputationStore(ema_by_uid={})
        return ReputationStore.from_json(data)
    except (OSError, ValueError, json.JSONDecodeError, TypeError, KeyError):
        return ReputationStore(ema_by_uid={})


def save_reputation(path: Path | None, store: ReputationStore) -> None:
    p = path or default_reputation_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(store.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def apply_ema_to_entries(
    entries: list[ScoredEntry],
    *,
    alpha: float,
    credibility_exponent: float,
    prev_ema: dict[int, float],
) -> tuple[list[ScoredEntry], dict[int, float], dict[int, float]]:
    """Return entries with ``reasoning_score``/``composite`` replaced by EMA-smoothed values.

    Returns ``(new_entries, new_ema_map, round_instant_scores)``.
    """
    raw_alpha = float(alpha)
    exp_p = max(0.0, float(credibility_exponent))
    instant: dict[int, float] = {e.uid: float(e.reasoning_score) for e in entries}
    new_ema: dict[int, float] = dict(prev_ema)

    out: list[ScoredEntry] = []
    for e in entries:
        r = float(e.reasoning_score)
        old = new_ema.get(e.uid, r)
        if raw_alpha <= 0.0:
            smoothed = r
        else:
            a = max(1e-9, min(1.0, raw_alpha))
            smoothed = a * r + (1.0 - a) * old
        new_ema[e.uid] = smoothed
        cred_mult = 1.0  # reserved: credibility EMA multiplier
        final = smoothed * (cred_mult**exp_p)
        out.append(
            ScoredEntry(
                uid=e.uid,
                reasoning_score=final,
                tokens=e.tokens,
                composite=final,
                submission_fp=e.submission_fp,
            ),
        )
    return out, new_ema, instant
