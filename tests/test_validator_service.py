from __future__ import annotations

from pathlib import Path

from lemma.common.config import LemmaSettings
from lemma.problems.known_theorems import known_theorems_manifest_sha256
from lemma.validator.profile import validator_profile_sha256
from lemma.validator.service import validator_startup_issues


def test_validator_startup_does_not_require_genesis_block(tmp_path: Path) -> None:
    base = LemmaSettings(
        _env_file=None,
        solved_ledger_path=tmp_path / "ledger.jsonl",
        target_genesis_block=None,
    )
    settings = base.model_copy(
        update={
            "known_theorems_manifest_expected_sha256": known_theorems_manifest_sha256(
                base.known_theorems_manifest_path,
            ),
            "validator_profile_expected_sha256": validator_profile_sha256(base),
        },
    )

    fatal, _warn = validator_startup_issues(settings, dry_run=False)

    assert fatal == []
