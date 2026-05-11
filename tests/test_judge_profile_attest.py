"""Tests for optional validator profile peer HTTP attest."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from lemma.common.config import LemmaSettings
from lemma.judge.profile import judge_profile_sha256
from lemma.validator.judge_profile_attest import (
    judge_profile_peer_check_errors,
    parse_peer_judge_hash,
    parse_peer_urls,
)


def test_parse_peer_urls_splits_commas() -> None:
    assert parse_peer_urls("http://a/x, http://b/y") == ["http://a/x", "http://b/y"]
    assert parse_peer_urls("") == []


def test_parse_peer_judge_hash_plain_and_json() -> None:
    h = "a" * 64
    assert parse_peer_judge_hash(h + "\n") == h
    assert parse_peer_judge_hash(f'0x{h}\n') == h
    assert parse_peer_judge_hash(f'{{"validator_profile_sha256":"{h}"}}') == h
    assert parse_peer_judge_hash(f'{{"judge_profile_sha256":"{h}"}}') == h


def test_attest_off_returns_empty() -> None:
    s = LemmaSettings.model_construct(lemma_judge_profile_attest_enabled=False)
    assert judge_profile_peer_check_errors(s) == []


def test_attest_skip_returns_empty() -> None:
    s = LemmaSettings.model_construct(
        lemma_judge_profile_attest_enabled=True,
        lemma_judge_profile_attest_allow_skip=True,
    )
    assert judge_profile_peer_check_errors(s) == []


def test_attest_no_urls_errors() -> None:
    s = LemmaSettings.model_construct(
        lemma_judge_profile_attest_enabled=True,
        lemma_judge_profile_attest_peer_urls="",
    )
    errs = judge_profile_peer_check_errors(s)
    assert len(errs) == 1
    assert "LEMMA_VALIDATOR_PROFILE_ATTEST_PEER_URLS" in errs[0]


def test_attest_peer_match_ok() -> None:
    s = LemmaSettings.model_construct(
        lemma_judge_profile_attest_enabled=True,
        lemma_judge_profile_attest_peer_urls="http://peer/hash",
    )
    want = judge_profile_sha256(s)
    mock_resp = MagicMock()
    mock_resp.text = want + "\n"
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("lemma.validator.judge_profile_attest.httpx.Client", return_value=mock_client):
        assert judge_profile_peer_check_errors(s) == []


def test_attest_peer_mismatch_errors() -> None:
    s = LemmaSettings.model_construct(
        lemma_judge_profile_attest_enabled=True,
        lemma_judge_profile_attest_peer_urls="http://peer/hash",
    )
    mock_resp = MagicMock()
    mock_resp.text = "b" * 64 + "\n"
    mock_resp.raise_for_status = MagicMock()
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.return_value = mock_resp

    with patch("lemma.validator.judge_profile_attest.httpx.Client", return_value=mock_client):
        errs = judge_profile_peer_check_errors(s)
    assert len(errs) == 1
    assert "align validator profiles" in errs[0]


def test_attest_http_error() -> None:
    import httpx

    s = LemmaSettings.model_construct(
        lemma_judge_profile_attest_enabled=True,
        lemma_judge_profile_attest_peer_urls="http://peer/hash",
    )
    mock_client = MagicMock()
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client.get.side_effect = httpx.HTTPError("boom")

    with patch("lemma.validator.judge_profile_attest.httpx.Client", return_value=mock_client):
        errs = judge_profile_peer_check_errors(s)
    assert len(errs) == 1
    assert "HTTP error" in errs[0]


@pytest.mark.parametrize(
    "body",
    ["", "not-json", '{"foo":1}', "zz"],
)
def test_parse_peer_judge_hash_invalid(body: str) -> None:
    assert parse_peer_judge_hash(body) is None
