"""Validator verify-credibility updates."""

from __future__ import annotations

from lemma.lean.sandbox import VerifyResult
from lemma.protocol import LemmaChallenge
from lemma.validator.epoch import _run_verify_batch, _update_verify_credibility


def _resp(*, proof_script: str = "namespace Submission\n") -> LemmaChallenge:
    return LemmaChallenge(
        theorem_id="gen/1",
        theorem_statement="theorem t : True := by sorry",
        lean_toolchain="lt",
        mathlib_rev="mr",
        deadline_unix=1,
        deadline_block=10,
        metronome_id="m1",
        proof_script=proof_script,
    )


def test_attest_trusted_verify_does_not_improve_credibility() -> None:
    resp = _resp()
    cred = {1: 0.25}

    _update_verify_credibility(
        cred,
        [(1, resp)],
        [(1, resp, VerifyResult(passed=True, reason="attest_trusted"))],
        alpha=1.0,
    )

    assert cred[1] == 0.25


def test_validator_lean_pass_improves_credibility() -> None:
    resp = _resp()
    cred = {1: 0.25}

    _update_verify_credibility(
        cred,
        [(1, resp)],
        [(1, resp, VerifyResult(passed=True, reason="ok"))],
        alpha=1.0,
    )

    assert cred[1] == 1.0


def test_validator_lean_failure_lowers_credibility() -> None:
    resp = _resp()
    cred = {1: 1.0}

    _update_verify_credibility(cred, [(1, resp)], [], alpha=0.5)

    assert cred[1] == 0.5


async def test_verify_batch_keeps_other_results_when_one_task_raises() -> None:
    good = _resp()
    bad = _resp()

    async def verify_one(
        uid: int,
        resp: LemmaChallenge,
    ) -> tuple[int, LemmaChallenge, VerifyResult] | None:
        if uid == 1:
            raise RuntimeError("boom")
        return uid, resp, VerifyResult(passed=True, reason="ok")

    verified = await _run_verify_batch([(1, bad), (2, good)], verify_one)

    assert len(verified) == 1
    assert verified[0][0] == 2
    assert verified[0][1] is good


async def test_verify_batch_reuses_identical_payload_result() -> None:
    first = _resp()
    second = _resp()
    calls: list[int] = []

    async def verify_one(
        uid: int,
        resp: LemmaChallenge,
    ) -> tuple[int, LemmaChallenge, VerifyResult] | None:
        calls.append(uid)
        return uid, resp, VerifyResult(passed=True, reason="ok")

    verified = await _run_verify_batch(
        [(1, first), (2, second)],
        verify_one,
        key_fn=lambda _uid, resp: resp.proof_script or "",
    )

    assert calls == [1]
    assert [(uid, resp) for uid, resp, _vr in verified] == [(1, first), (2, second)]


async def test_verify_batch_keeps_distinct_payloads_separate() -> None:
    first = _resp(proof_script="exact trivial\n")
    second = _resp(proof_script="by trivial\n")
    calls: list[int] = []

    async def verify_one(
        uid: int,
        resp: LemmaChallenge,
    ) -> tuple[int, LemmaChallenge, VerifyResult] | None:
        calls.append(uid)
        return uid, resp, VerifyResult(passed=True, reason="ok")

    verified = await _run_verify_batch(
        [(1, first), (2, second)],
        verify_one,
        key_fn=lambda _uid, resp: resp.proof_script or "",
    )

    assert calls == [1, 2]
    assert [(uid, resp) for uid, resp, _vr in verified] == [(1, first), (2, second)]
