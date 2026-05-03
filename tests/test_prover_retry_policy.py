"""Prover retry backoff — skip retries when failure is clearly billing/quota."""

from __future__ import annotations

from lemma.common.async_llm_retry import fail_fast_instead_of_retry


def test_fail_fast_on_gemini_prepayment_depleted() -> None:
    err = Exception(
        "Error code: 429 - [{'error': {'message': 'Your prepayment credits are depleted. "
        "Please go to AI Studio ...'}}]"
    )
    assert fail_fast_instead_of_retry(err) is True


def test_retry_normal_rate_limit() -> None:
    err = Exception("Error code: 429 - Infrastructure is at maximum capacity")
    assert fail_fast_instead_of_retry(err) is False
