"""Current-epoch cadence reward math."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewardCandidate:
    uid: int
    commitment_block: int
    pareto_layer: int = 0
    reign_count: int = 0


def base_reward(solve_count: int, eligible_count: int) -> float:
    if solve_count <= 0 or eligible_count <= 0:
        return 0.0
    fraction = min(1.0, max(0.0, float(solve_count) / float(eligible_count)))
    return (1.0 - fraction) ** 2


def cadence_epoch_weights(
    *,
    candidates: list[RewardCandidate],
    eligible_count: int,
    owner_burn_uid: int,
) -> dict[int, float]:
    """Return miner weights plus the owner/burn remainder for one validator epoch."""
    unique = _first_candidate_per_uid(candidates)
    earned = base_reward(len(unique), eligible_count)
    out: dict[int, float] = {}
    if earned > 0.0:
        raw = _ranked_raw_weights(unique)
        raw_total = sum(raw.values())
        if raw_total > 0.0:
            for uid, weight in raw.items():
                out[uid] = earned * weight / raw_total
    out[int(owner_burn_uid)] = out.get(int(owner_burn_uid), 0.0) + max(0.0, 1.0 - sum(out.values()))
    return {uid: weight for uid, weight in out.items() if weight > 0.0}


def _first_candidate_per_uid(candidates: list[RewardCandidate]) -> list[RewardCandidate]:
    best: dict[int, RewardCandidate] = {}
    for candidate in candidates:
        current = best.get(candidate.uid)
        if current is None or _candidate_sort_key(candidate) < _candidate_sort_key(current):
            best[candidate.uid] = candidate
    return sorted(best.values(), key=_candidate_sort_key)


def _candidate_sort_key(candidate: RewardCandidate) -> tuple[int, int, int, int]:
    return (candidate.commitment_block, candidate.pareto_layer, candidate.reign_count, candidate.uid)


def _ranked_raw_weights(candidates: list[RewardCandidate]) -> dict[int, float]:
    out: dict[int, float] = {}
    groups: list[list[int]] = []
    previous_key: tuple[int, int, int] | None = None
    for candidate in candidates:
        key = (candidate.commitment_block, candidate.pareto_layer, candidate.reign_count)
        if key != previous_key:
            groups.append([])
            previous_key = key
        groups[-1].append(candidate.uid)
    for rank, group in enumerate(groups):
        share = 0.5**rank
        for uid in group:
            out[uid] = share
    return out
