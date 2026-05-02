"""Judge profile hashing for subnet parity."""

from lemma.common.config import LemmaSettings
from lemma.judge.profile import judge_profile_dict, judge_profile_sha256


def test_judge_profile_openai_includes_base_url() -> None:
    s = LemmaSettings(
        judge_provider="openai",
        openai_model="Qwen/Qwen3-32B-TEE",
        openai_base_url="https://llm.chutes.ai/v1",
        judge_temperature=0.2,
        judge_max_tokens=256,
    )
    d = judge_profile_dict(s)
    assert d["openai_model"] == "Qwen/Qwen3-32B-TEE"
    assert d["openai_base_url"] == "https://llm.chutes.ai/v1"
    assert "anthropic_model" not in d


def test_judge_profile_stable_sha256() -> None:
    s = LemmaSettings(
        judge_provider="openai",
        openai_model="test-model",
        openai_base_url="http://localhost:8000/v1",
        judge_temperature=0.2,
        judge_max_tokens=256,
    )
    assert judge_profile_sha256(s) == judge_profile_sha256(s)


def test_judge_profile_base_url_trailing_slash_normalized() -> None:
    a = LemmaSettings(
        judge_provider="openai",
        openai_model="m",
        openai_base_url="http://localhost:8000/v1/",
        judge_temperature=0.2,
        judge_max_tokens=256,
    )
    b = LemmaSettings(
        judge_provider="openai",
        openai_model="m",
        openai_base_url="http://localhost:8000/v1",
        judge_temperature=0.2,
        judge_max_tokens=256,
    )
    assert judge_profile_sha256(a) == judge_profile_sha256(b)
