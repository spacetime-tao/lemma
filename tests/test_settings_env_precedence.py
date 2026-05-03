"""LemmaSettings prefers `.env` over process environment (unless LEMMA_PREFER_PROCESS_ENV)."""

from __future__ import annotations

import pytest
from lemma.common.config import CANONICAL_JUDGE_OPENAI_MODEL, LemmaSettings


def test_dotenv_beats_process_env_for_openai_model(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f'OPENAI_MODEL="{CANONICAL_JUDGE_OPENAI_MODEL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "legacy/from-shell")
    s = LemmaSettings(_env_file=str(env_file))
    assert s.openai_model == CANONICAL_JUDGE_OPENAI_MODEL


def test_process_env_beats_dotenv_when_flag(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("LEMMA_PREFER_PROCESS_ENV", "1")
    env_file = tmp_path / ".env"
    env_file.write_text(f'OPENAI_MODEL="{CANONICAL_JUDGE_OPENAI_MODEL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "legacy/from-shell")
    s = LemmaSettings(_env_file=str(env_file))
    assert s.openai_model == "legacy/from-shell"


def test_dotenv_sets_lean_use_docker(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    monkeypatch.delenv("LEMMA_USE_DOCKER", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("LEMMA_USE_DOCKER=false\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    s = LemmaSettings(_env_file=str(env_file))
    assert s.lean_use_docker is False


def test_explicit_init_kwarg_beats_all(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.delenv("LEMMA_PREFER_PROCESS_ENV", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(f'OPENAI_MODEL="{CANONICAL_JUDGE_OPENAI_MODEL}"\n', encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_MODEL", "legacy/from-shell")
    s = LemmaSettings(_env_file=str(env_file), openai_model="explicit")
    assert s.openai_model == "explicit"
