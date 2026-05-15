"""Target commit/reveal phase calculation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lemma.common.config import LemmaSettings
from lemma.ledger import SolvedLedgerEntry

TargetPhaseName = Literal["pending", "commit", "reveal"]


@dataclass(frozen=True)
class TargetPhase:
    name: TargetPhaseName
    current_block: int
    target_start_block: int
    commit_cutoff_block: int
    reveal_block: int

    @property
    def blocks_until_reveal(self) -> int:
        return max(0, self.reveal_block - self.current_block)


def target_start_block(settings: LemmaSettings, matching_ledger: list[SolvedLedgerEntry]) -> int:
    if matching_ledger:
        return int(matching_ledger[-1].accepted_block) + 1
    if settings.target_genesis_block is None:
        raise ValueError("LEMMA_TARGET_GENESIS_BLOCK is required before the first target can run")
    return int(settings.target_genesis_block)


def target_phase(settings: LemmaSettings, matching_ledger: list[SolvedLedgerEntry], current_block: int) -> TargetPhase:
    start = target_start_block(settings, matching_ledger)
    cutoff = start + int(settings.commit_window_blocks) - 1
    reveal = cutoff + 1
    if current_block < start:
        name: TargetPhaseName = "pending"
    elif current_block <= cutoff:
        name = "commit"
    else:
        name = "reveal"
    return TargetPhase(
        name=name,
        current_block=int(current_block),
        target_start_block=start,
        commit_cutoff_block=cutoff,
        reveal_block=reveal,
    )
