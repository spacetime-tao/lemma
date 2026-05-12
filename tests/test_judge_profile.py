"""Judge profile hashing for subnet parity."""

from lemma.common.config import LemmaSettings
from lemma.judge.profile import judge_profile_dict, judge_profile_sha256


def test_profile_ignores_optional_judge_stack() -> None:
    a = LemmaSettings(
        judge_provider="openai",
        openai_model="Qwen/Qwen3-32B-TEE",
        openai_base_url="https://llm.chutes.ai/v1",
        judge_temperature=0.2,
        judge_max_tokens=256,
    )
    b = LemmaSettings(
        judge_provider="anthropic",
        openai_model="local-model",
        openai_base_url="http://127.0.0.1:8000/v1",
        judge_temperature=1.0,
        judge_max_tokens=1024,
    )

    assert judge_profile_sha256(a) == judge_profile_sha256(b)
    d = judge_profile_dict(a)
    assert "judge_provider" not in d
    assert "rubric_sha256" not in d
    assert "openai_model" not in d


def test_judge_profile_includes_validator_scoring_policy() -> None:
    s = LemmaSettings(
        problem_seed_quantize_blocks=55,
        lemma_problem_seed_chain_head_slack_blocks=1,
        lean_verify_timeout_s=123,
        forward_wait_min_s=10,
        forward_wait_max_s=100,
        timeout_scale_by_split=True,
        timeout_split_easy_mult=1.1,
        timeout_split_medium_mult=1.2,
        timeout_split_hard_mult=1.3,
        lemma_reputation_credibility_exponent=2.0,
        lemma_epoch_problem_count=3,
        lemma_commit_reveal_enabled=True,
        lemma_miner_verify_attest_enabled=True,
        lemma_miner_verify_attest_spot_verify_fraction=0.25,
        lemma_miner_verify_attest_spot_verify_salt="secret",
    )
    d = judge_profile_dict(s)

    assert d["profile_schema"] == "lemma_validator_profile_v6"
    assert d["problem_policy"]["problem_seed_quantize_blocks"] == 55
    assert d["problem_policy"]["hybrid_generated_weight"] == 60
    assert d["problem_policy"]["hybrid_catalog_weight"] == 40
    assert d["verification_policy"]["lean_sandbox_image"] == "lemma/lean-sandbox:latest"
    assert d["verification_policy"]["lean_verify_timeout_s"] == 123
    assert d["verification_policy"]["timeout_split_hard_mult"] == 1.3
    assert d["scoring_policy"]["lemma_reputation_credibility_exponent"] == 2.0
    assert d["scoring_policy"]["lemma_epoch_problem_count"] == 3
    assert d["scoring_policy"]["lemma_scoring_coldkey_partition"] is True
    assert d["protocol_policy"]["lemma_commit_reveal_enabled"] is True
    assert d["protocol_policy"]["lemma_miner_verify_attest_spot_verify_fraction"] == 0.25
    salt_hash = d["protocol_policy"]["lemma_miner_verify_attest_spot_verify_salt_sha256"]
    assert isinstance(salt_hash, str)
    assert len(salt_hash) == 64
    assert "secret" not in salt_hash


def test_default_reputation_credibility_exponent_is_linear_policy(monkeypatch) -> None:
    monkeypatch.delenv("LEMMA_REPUTATION_CREDIBILITY_EXPONENT", raising=False)
    s = LemmaSettings(_env_file=None)
    assert s.lemma_reputation_credibility_exponent == 1.0
    assert judge_profile_dict(s)["scoring_policy"]["lemma_reputation_credibility_exponent"] == 1.0


def test_judge_profile_hash_changes_when_reputation_policy_changes() -> None:
    a = LemmaSettings(lemma_reputation_credibility_exponent=1.0)
    b = LemmaSettings(lemma_reputation_credibility_exponent=2.0)
    assert judge_profile_sha256(a) != judge_profile_sha256(b)


def test_judge_profile_hash_changes_when_coldkey_partition_changes() -> None:
    a = LemmaSettings(lemma_scoring_coldkey_partition=True)
    b = LemmaSettings(lemma_scoring_coldkey_partition=False)
    assert judge_profile_sha256(a) != judge_profile_sha256(b)


def test_judge_profile_hash_changes_when_attest_spot_salt_changes() -> None:
    a = LemmaSettings(lemma_miner_verify_attest_spot_verify_salt="a")
    b = LemmaSettings(lemma_miner_verify_attest_spot_verify_salt="b")
    assert judge_profile_sha256(a) != judge_profile_sha256(b)


def test_judge_profile_hash_changes_when_sandbox_image_changes() -> None:
    a = LemmaSettings(lean_sandbox_image="lemma/lean-sandbox:latest")
    b = LemmaSettings(lean_sandbox_image="registry.example/lemma/lean-sandbox@sha256:abc")
    assert judge_profile_sha256(a) != judge_profile_sha256(b)


def test_judge_profile_stable_sha256() -> None:
    s = LemmaSettings(
        judge_provider="openai",
        openai_model="test-model",
        openai_base_url="http://localhost:8000/v1",
        judge_temperature=0.2,
        judge_max_tokens=256,
    )
    assert judge_profile_sha256(s) == judge_profile_sha256(s)
