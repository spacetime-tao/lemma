"""Difficulty-weighted rolling score rewards."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RollingScoreStore:
    rolling_score_by_uid: dict[int, float] = field(default_factory=dict)
    version: int = 3

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> RollingScoreStore:
        raw_any = data.get("rolling_score_by_uid")
        if not isinstance(raw_any, dict) or not raw_any:
            legacy = data.get("ema_by_uid")
            raw_any = legacy if isinstance(legacy, dict) else {}
        return cls(
            rolling_score_by_uid={int(uid): _clamp(float(score)) for uid, score in raw_any.items()},
            version=max(3, int(data.get("version", 3))),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "rolling_score_by_uid": {str(uid): score for uid, score in sorted(self.rolling_score_by_uid.items())},
        }


def default_rolling_score_path() -> Path:
    return Path.home() / ".lemma" / "validator_reputation.json"


def load_rolling_scores(path: Path | None) -> RollingScoreStore:
    p = path or default_rolling_score_path()
    if not p.exists():
        return RollingScoreStore()
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return RollingScoreStore()
    if not isinstance(raw, dict):
        return RollingScoreStore()
    return RollingScoreStore.from_json(raw)


def save_rolling_scores(path: Path | None, store: RollingScoreStore) -> None:
    p = path or default_rolling_score_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(store.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(p)


def rolling_effective_alpha(alpha: float, difficulty_weight: float) -> float:
    a = max(0.0, min(1.0, float(alpha)))
    w = max(0.0, float(difficulty_weight))
    if a <= 0.0 or w <= 0.0:
        return 0.0
    return _clamp(1.0 - ((1.0 - a) ** w))


def apply_rolling_outcomes(
    scores: dict[int, float],
    outcomes: dict[int, bool],
    *,
    alpha: float,
    difficulty_weight: float,
) -> dict[int, float]:
    eff_alpha = rolling_effective_alpha(alpha, difficulty_weight)
    for uid, passed in outcomes.items():
        old = _clamp(scores.get(int(uid), 0.0))
        target = 1.0 if passed else 0.0
        scores[int(uid)] = _clamp((1.0 - eff_alpha) * old + eff_alpha * target)
    return scores


def rolling_weights(scores: dict[int, float]) -> dict[int, float]:
    positive = {int(uid): _clamp(score) for uid, score in scores.items() if _clamp(score) > 0.0}
    total = sum(positive.values())
    if total <= 0.0:
        return {}
    return {uid: score / total for uid, score in positive.items()}


def partition_same_coldkey_weights(
    weights: dict[int, float],
    coldkeys_by_uid: dict[int, str | None],
) -> dict[int, float]:
    groups: dict[str, list[int]] = {}
    for uid in weights:
        coldkey = (coldkeys_by_uid.get(uid) or f"uid:{uid}").strip() or f"uid:{uid}"
        groups.setdefault(coldkey, []).append(uid)

    adjusted = {uid: max(0.0, float(weight)) for uid, weight in weights.items()}
    for uids in groups.values():
        if len(uids) < 2:
            continue
        group_total = sum(adjusted[uid] for uid in uids)
        group_cap = max(adjusted[uid] for uid in uids)
        if group_total <= 0.0 or group_cap >= group_total:
            continue
        scale = group_cap / group_total
        for uid in uids:
            adjusted[uid] *= scale

    total = sum(adjusted.values())
    if total <= 0.0:
        return {}
    return {uid: weight / total for uid, weight in adjusted.items()}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))
