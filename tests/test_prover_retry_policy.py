"""Prover retry backoff — skip retries when failure is clearly billing/quota."""

from __future__ import annotations

from lemma.miner.prover import _fail_fast_instead_of_retry


def test_fail_fast_on_gemini_prepayment_depleted() -> None:
    err = Exception(
        "Error code: 429 - [{'error': {'message': 'Your prepayment credits are depleted. "
        "Please go to AI Studio ...'}}]"
    )
    assert _fail_fast_instead_of_retry(err) is True


def test_retry_normal_rate_limit() -> None:
    err = Exception("Error code: 429 - Infrastructure is at maximum capacity")
    assert _fail_fast_instead_of_retry(err) is False
