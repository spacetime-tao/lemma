"""Validator startup gates for proof-only scoring."""

from lemma.common.config import LemmaSettings
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.hybrid import problem_supply_registry_sha256
from lemma.validator.service import validator_startup_issues


def _pinned_settings(**updates: object) -> LemmaSettings:
    base = LemmaSettings(
        _env_file=None,
        generated_registry_expected_sha256=generated_registry_sha256(),
        problem_supply_registry_expected_sha256=problem_supply_registry_sha256(),
        **updates,
    )
    return base.model_copy(update={"judge_profile_expected_sha256": judge_profile_sha256(base)})


def test_live_validator_does_not_require_judge_key_for_proof_only_scoring(
    monkeypatch,
) -> None:
    monkeypatch.delenv("LEMMA_FAKE_JUDGE", raising=False)
    settings = _pinned_settings(judge_openai_api_key=None, openai_api_key=None)

    fatal, warn = validator_startup_issues(settings, dry_run=False)

    assert fatal == []
    assert warn == []


def test_live_validator_ignores_optional_judge_provider_for_proof_only_scoring(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LEMMA_FAKE_JUDGE", "1")
    settings = _pinned_settings(judge_provider="anthropic", openai_model="local-model")

    fatal, warn = validator_startup_issues(settings, dry_run=False)

    assert fatal == []
    assert warn == []
