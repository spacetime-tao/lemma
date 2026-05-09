"""Validator judge selection."""

from __future__ import annotations

import pytest
from lemma.common.config import LemmaSettings
from lemma.judge.fake import FakeJudge
from lemma.validator.epoch import _build_judge


def _settings_without_keys() -> LemmaSettings:
    return LemmaSettings(
        _env_file=None,
        judge_openai_api_key=None,
        openai_api_key=None,
        anthropic_api_key=None,
    )


def test_dry_run_uses_fake_judge_without_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    monkeypatch.delenv("LEMMA_DRY_RUN_REAL_JUDGE", raising=False)

    assert isinstance(_build_judge(_settings_without_keys(), dry_run=True), FakeJudge)


def test_live_validator_rejects_missing_judge_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)

    with pytest.raises(RuntimeError, match="missing"):
        _build_judge(_settings_without_keys(), dry_run=False)


def test_live_validator_rejects_forced_fake_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEMMA_FAKE_JUDGE", "1")

    with pytest.raises(RuntimeError, match="dry-run"):
        _build_judge(_settings_without_keys(), dry_run=False)
