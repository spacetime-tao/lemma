"""Miner daily forward cap."""

from pathlib import Path

import pytest
from lemma.miner.daily_budget import allow_daily_forward


def test_unlimited_zero(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    for _ in range(5):
        assert allow_daily_forward(0, state_path=p) is True


def test_cap_resets_utc_day(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import lemma.miner.daily_budget as db

    p = tmp_path / "s.json"
    monkeypatch.setattr(db, "_utc_day", lambda: "2030-01-01")
    assert allow_daily_forward(2, state_path=p) is True
    assert allow_daily_forward(2, state_path=p) is True
    assert allow_daily_forward(2, state_path=p) is False

    monkeypatch.setattr(db, "_utc_day", lambda: "2030-01-02")
    assert allow_daily_forward(2, state_path=p) is True


def test_persist_across_instantiation(tmp_path: Path) -> None:
    p = tmp_path / "s.json"
    assert allow_daily_forward(1, state_path=p) is True
    assert allow_daily_forward(1, state_path=p) is False
