"""Validator verify-credibility updates."""

from __future__ import annotations

from lemma.lean.sandbox import VerifyResult
from lemma.protocol import LemmaChallenge
from lemma.validator.epoch import _run_verify_batch, _update_verify_credibility


def _resp() -> LemmaChallenge:
    return LemmaChallenge(
        theorem_id="gen/1",
        theorem_statement="theorem t : True := by sorry",
        lean_toolchain="lt",
        mathlib_rev="mr",
        deadline_unix=1,
        deadline_block=10,
        metronome_id="m1",
        proof_script="namespace Submission\n",
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
