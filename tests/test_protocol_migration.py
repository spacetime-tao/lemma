from lemma.common.config import LemmaSettings
from lemma.validator.protocol_migration import validate_protocol_feature_flags


def test_validate_flags_ok_by_default() -> None:
    validate_protocol_feature_flags(LemmaSettings())


def test_validate_flags_ok_with_commit_reveal() -> None:
    validate_protocol_feature_flags(
        LemmaSettings.model_construct(lemma_commit_reveal_enabled=True),
    )


def test_validate_flags_ok_with_judge_profile_attest() -> None:
    validate_protocol_feature_flags(
        LemmaSettings.model_construct(lemma_judge_profile_attest_enabled=True),
    )
