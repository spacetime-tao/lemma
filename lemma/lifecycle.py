"""Target commit/reveal phase calculation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from lemma.cadence import cadence_window
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
    del matching_ledger
    return cadence_window(int(settings.target_genesis_block or 0), int(settings.cadence_window_blocks)).seed


def target_phase(settings: LemmaSettings, matching_ledger: list[SolvedLedgerEntry], current_block: int) -> TargetPhase:
    del matching_ledger
    start = cadence_window(int(current_block), int(settings.cadence_window_blocks)).seed
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
