from __future__ import annotations

from pathlib import Path

from lemma.common.config import LemmaSettings
from lemma.validator.service import validator_startup_issues


def test_missing_genesis_block_is_startup_fatal_on_empty_ledger(tmp_path: Path) -> None:
    settings = LemmaSettings(
        _env_file=None,
        solved_ledger_path=tmp_path / "ledger.jsonl",
        target_genesis_block=None,
    )

    fatal, _warn = validator_startup_issues(settings, dry_run=False)

    assert "LEMMA_TARGET_GENESIS_BLOCK" in "\n".join(fatal)
