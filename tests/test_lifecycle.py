from __future__ import annotations

import pytest
from lemma.common.config import LemmaSettings
from lemma.ledger import LedgerSolver, SolvedLedgerEntry
from lemma.lifecycle import target_phase, target_start_block


def _settings(**updates: object) -> LemmaSettings:
    base = {"_env_file": None, "target_genesis_block": 100, "commit_window_blocks": 25}
    base.update(updates)
    return LemmaSettings(**base)


def _entry(accepted_block: int = 200) -> SolvedLedgerEntry:
    return SolvedLedgerEntry(
        target_id="known/test/one",
        solvers=(
            LedgerSolver(
                uid=1,
                hotkey="hotkey",
                coldkey=None,
                proof_sha256="a" * 64,
                verify_reason="ok",
                build_seconds=0.0,
            ),
        ),
        accepted_block=accepted_block,
        accepted_unix=1,
        validator_hotkey="validator",
        lemma_version="0.1.0",
        theorem_statement_sha256="b" * 64,
    )


def test_missing_genesis_blocks_empty_ledger_start() -> None:
    with pytest.raises(ValueError, match="LEMMA_TARGET_GENESIS_BLOCK"):
        target_start_block(_settings(target_genesis_block=None), [])


def test_first_target_phases_from_genesis() -> None:
    settings = _settings(target_genesis_block=100, commit_window_blocks=3)

    assert target_phase(settings, [], 99).name == "pending"
    commit = target_phase(settings, [], 100)
    assert commit.name == "commit"
    assert commit.commit_cutoff_block == 102
    reveal = target_phase(settings, [], 103)
    assert reveal.name == "reveal"
    assert reveal.reveal_block == 103


def test_next_target_starts_after_previous_acceptance() -> None:
    settings = _settings(target_genesis_block=100, commit_window_blocks=2)
    phase = target_phase(settings, [_entry(accepted_block=200)], 201)

    assert phase.target_start_block == 201
    assert phase.name == "commit"
    assert phase.reveal_block == 203
