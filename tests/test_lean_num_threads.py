"""LEAN_NUM_THREADS wiring for Lean sandbox."""

import pytest

from lemma.lean.sandbox import _lean_num_threads_value, _merge_lean_process_env


def test_lean_num_threads_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEMMA_LEAN_NUM_THREADS", "7")
    assert _lean_num_threads_value() == "7"


def test_merge_lean_process_env_sets_threads(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_LEAN_NUM_THREADS", raising=False)
    monkeypatch.delenv("LEAN_NUM_THREADS", raising=False)
    out = _merge_lean_process_env({})
    assert "LEAN_NUM_THREADS" in out
    assert int(out["LEAN_NUM_THREADS"]) >= 1


def test_merge_respects_existing_lean_num_threads() -> None:
    out = _merge_lean_process_env({"LEAN_NUM_THREADS": "3"})
    assert out["LEAN_NUM_THREADS"] == "3"
