"""Shared cadence window and UID-variant helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from lemma.problems.base import Problem, ProblemSource

DEFAULT_CADENCE_WINDOW_BLOCKS = 100
DEFAULT_BLOCK_TIME_SECONDS = 12.0
SPLIT_WEIGHTS: dict[str, int] = {"easy": 10, "medium": 35, "hard": 50, "extreme": 5}
DIFFICULTY_SCORE_WEIGHTS: dict[str, float] = {"easy": 1.0, "medium": 2.0, "hard": 4.0, "extreme": 8.0}


@dataclass(frozen=True)
class CadenceWindow:
    block: int
    seed: int
    window_blocks: int

    @property
    def start_block(self) -> int:
        return self.seed

    @property
    def end_block(self) -> int:
        return self.seed + self.window_blocks - 1

    @property
    def next_rotation_block(self) -> int:
        return self.seed + self.window_blocks

    @property
    def blocks_until_rotation(self) -> int:
        return max(0, self.next_rotation_block - self.block)

    def eta_seconds(self, seconds_per_block: float = DEFAULT_BLOCK_TIME_SECONDS) -> int:
        return int(round(self.blocks_until_rotation * max(0.0, float(seconds_per_block))))


def cadence_window(block: int, window_blocks: int = DEFAULT_CADENCE_WINDOW_BLOCKS) -> CadenceWindow:
    size = max(1, int(window_blocks))
    head = max(0, int(block))
    return CadenceWindow(block=head, seed=(head // size) * size, window_blocks=size)


def previous_seed(seed: int, window_blocks: int = DEFAULT_CADENCE_WINDOW_BLOCKS) -> int:
    return max(0, int(seed) - max(1, int(window_blocks)))


def next_seed(seed: int, window_blocks: int = DEFAULT_CADENCE_WINDOW_BLOCKS) -> int:
    return int(seed) + max(1, int(window_blocks))


def uid_variant_seed(seed: int, uid: int) -> int:
    digest = hashlib.sha256(f"{int(seed)}:{int(uid)}".encode()).digest()
    return int.from_bytes(digest[:8], "big")


def cadence_problem(source: ProblemSource, seed: int) -> Problem:
    return source.sample(seed=int(seed))


def uid_cadence_problem(
    source: ProblemSource,
    anchor: Problem,
    *,
    seed: int,
    uid: int,
    variants_enabled: bool,
) -> Problem:
    if not variants_enabled:
        return anchor
    return source.sample(seed=uid_variant_seed(seed, uid), split=anchor.split)


def cadence_poll_id(seed: int, uid: int | None, *, variants_enabled: bool) -> str:
    if variants_enabled and uid is not None:
        return f"{int(seed)}:{int(uid)}"
    return str(int(seed))


def difficulty_score_weight(split: str, overrides: dict[str, float] | None = None) -> float:
    weights = overrides or DIFFICULTY_SCORE_WEIGHTS
    return float(weights.get((split or "").strip().lower(), 1.0))


def format_eta(seconds: int) -> str:
    sec = max(0, int(seconds))
    if sec >= 3600:
        return f"about {sec / 3600:.1f} hours"
    if sec >= 60:
        return f"about {round(sec / 60)} minutes"
    return f"about {sec} seconds"
