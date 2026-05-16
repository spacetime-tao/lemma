"""Per-UID validator scoring state persisted on disk."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from lemma.scoring.pareto import ScoredEntry


@dataclass
class ReputationStore:
    """Versioned per-UID scoring state."""

    ema_by_uid: dict[int, float]
    credibility_by_uid: dict[int, float] = field(default_factory=dict)
    rolling_score_by_uid: dict[int, float] = field(default_factory=dict)
    version: int = 3

    def to_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "rolling_score_by_uid": {str(k): v for k, v in sorted(self.rolling_score_by_uid.items())},
            "ema_by_uid": {str(k): v for k, v in sorted(self.ema_by_uid.items())},
            "credibility_by_uid": {
                str(k): v for k, v in sorted(self.credibility_by_uid.items())
            },
        }

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> ReputationStore:
        ver = int(data.get("version", 2))
        raw = data.get("ema_by_uid") or {}
        ema: dict[int, float] = {}
        for k, v in raw.items():
            ema[int(k)] = float(v)
        raw_r = data.get("rolling_score_by_uid") or {}
        rolling: dict[int, float] = {}
        if isinstance(raw_r, dict):
            for k, v in raw_r.items():
                rolling[int(k)] = _clamp_score(float(v))
        cred: dict[int, float] = {}
        raw_c = data.get("credibility_by_uid")
        if isinstance(raw_c, dict):
            for k, v in raw_c.items():
                cred[int(k)] = float(v)
        if not rolling and ver < 3:
            rolling = {uid: _clamp_score(score) for uid, score in ema.items()}
        return cls(ema_by_uid=ema, credibility_by_uid=cred, rolling_score_by_uid=rolling, version=max(3, ver))


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


def rolling_effective_alpha(alpha: float, difficulty_weight: float) -> float:
    """Difficulty-weighted EMA alpha."""
    a = max(0.0, min(1.0, float(alpha)))
    w = max(0.0, float(difficulty_weight))
    if a <= 0.0 or w <= 0.0:
        return 0.0
    eff = 1.0 - ((1.0 - a) ** w)
    return max(0.0, min(1.0, float(eff)))


def apply_rolling_outcomes(
    scores: dict[int, float],
    outcomes: dict[int, bool],
    *,
    alpha: float,
    difficulty_weight: float,
) -> dict[int, float]:
    """Update per-UID rolling pass/fail scores in place and return them."""
    pass_weight = max(0.0, float(difficulty_weight))
    miss_weight = (1.0 / pass_weight) if pass_weight > 0.0 else 0.0
    pass_alpha = rolling_effective_alpha(alpha, pass_weight)
    miss_alpha = rolling_effective_alpha(alpha, miss_weight)
    for uid, passed in outcomes.items():
        old = _clamp_score(scores.get(int(uid), 0.0))
        eff_alpha = pass_alpha if passed else miss_alpha
        target = 1.0 if passed else 0.0
        scores[int(uid)] = _clamp_score((1.0 - eff_alpha) * old + eff_alpha * target)
    return scores


def rolling_weights(scores: dict[int, float]) -> dict[int, float]:
    """Normalize positive rolling scores into validator weights."""
    raw = {int(uid): _clamp_score(score) for uid, score in scores.items() if _clamp_score(score) > 0.0}
    total = sum(raw.values())
    if total <= 0.0:
        return {}
    return {uid: score / total for uid, score in raw.items()}


def _clamp_score(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def apply_ema_to_entries(
    entries: list[ScoredEntry],
    *,
    alpha: float,
    credibility_exponent: float,
    prev_ema: dict[int, float],
    credibility_by_uid: dict[int, float] | None = None,
) -> tuple[list[ScoredEntry], dict[int, float]]:
    """Return entries with ``score`` replaced by EMA-smoothed values.

    ``credibility_by_uid`` holds per-UID verify-pass EMA in ``[0, 1]`` (default 1.0 if missing).
    Final score uses ``smoothed * (credibility ** credibility_exponent)``.

    Returns ``(new_entries, new_ema_map)``.
    """
    raw_alpha = float(alpha)
    exp_p = max(0.0, float(credibility_exponent))
    cred_map = credibility_by_uid or {}
    new_ema: dict[int, float] = dict(prev_ema)

    out: list[ScoredEntry] = []
    for e in entries:
        r = float(e.score)
        old = new_ema.get(e.uid, r)
        if raw_alpha <= 0.0:
            smoothed = r
        else:
            a = max(1e-9, min(1.0, raw_alpha))
            smoothed = a * r + (1.0 - a) * old
        new_ema[e.uid] = smoothed
        cred_mult = max(0.0, min(1.0, float(cred_map.get(e.uid, 1.0))))
        final = smoothed * (cred_mult**exp_p)
        out.append(
            ScoredEntry(
                uid=e.uid,
                score=final,
                cost=e.cost,
                submission_fp=e.submission_fp,
            ),
        )
    return out, new_ema
