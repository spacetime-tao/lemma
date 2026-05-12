"""Validator refuses host Lean without explicit acknowledgement."""

import pytest
from lemma.common.config import LemmaSettings
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.hybrid import problem_supply_registry_sha256
from lemma.validator.service import _require_docker_for_validator, validator_startup_issues


def _ready_settings(**updates: object) -> LemmaSettings:
    fields = {
        "lean_use_docker": True,
        "problem_source": "generated",
        "generated_registry_expected_sha256": generated_registry_sha256(),
        **updates,
    }
    settings = LemmaSettings(_env_file=None, **fields)
    if "judge_profile_expected_sha256" not in updates:
        settings = settings.model_copy(update={"judge_profile_expected_sha256": judge_profile_sha256(settings)})
    return settings


def test_validator_requires_docker_by_default() -> None:
    s = LemmaSettings().model_copy(update={"lean_use_docker": False})
    with pytest.raises(SystemExit, match="requires Docker"):
        _require_docker_for_validator(s)


def test_validator_ok_when_docker_on() -> None:
    s = LemmaSettings().model_copy(update={"lean_use_docker": True})
    _require_docker_for_validator(s)


def test_validator_startup_issues_accept_ready_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    fatal, warn = validator_startup_issues(_ready_settings(), dry_run=False)
    assert fatal == []
    assert warn == []


def test_validator_startup_issues_accept_ready_hybrid_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    settings = LemmaSettings(
        _env_file=None,
        lean_use_docker=True,
        problem_source="hybrid",
        problem_supply_registry_expected_sha256=problem_supply_registry_sha256(),
    )
    settings = settings.model_copy(update={"judge_profile_expected_sha256": judge_profile_sha256(settings)})
    fatal, warn = validator_startup_issues(settings, dry_run=False)
    assert fatal == []
    assert warn == []


def test_validator_startup_issues_match_docker_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    fatal, _ = validator_startup_issues(_ready_settings(lean_use_docker=False), dry_run=False)
    assert any("requires Docker" in msg for msg in fatal)


def test_validator_startup_issues_reject_bad_pins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = _ready_settings(judge_profile_expected_sha256="0" * 64)
    fatal, _ = validator_startup_issues(s, dry_run=False)
    assert any("validator profile mismatch" in msg for msg in fatal)


def test_validator_startup_issues_live_key_not_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    s = _ready_settings(judge_openai_api_key=None, openai_api_key=None)
    live_fatal, _ = validator_startup_issues(s, dry_run=False)
    dry_fatal, _ = validator_startup_issues(s, dry_run=True)
    assert not any("missing" in msg for msg in live_fatal)
    assert not any("missing" in msg for msg in dry_fatal)
