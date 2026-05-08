"""Miner verify attestation helpers."""

import tempfile

import bittensor as bt
from lemma.protocol import LemmaChallenge
from lemma.protocol_attest import (
    attest_spot_should_full_verify,
    miner_verify_attest_message,
    sign_miner_verify_attest,
    verify_miner_verify_attest_signature,
)


def test_miner_verify_attest_message_stable() -> None:
    s = LemmaChallenge(
        theorem_id="gen/1",
        theorem_statement="theorem t : True := by sorry",
        imports=["Mathlib"],
        lean_toolchain="lt",
        mathlib_rev="mr",
        deadline_unix=1,
        metronome_id="m99",
        deadline_block=None,
        proof_script="namespace Submission\n",
    )
    a = miner_verify_attest_message(s)
    b = miner_verify_attest_message(s)
    assert a == b
    assert len(a) > 32


def test_sign_verify_roundtrip() -> None:
    # CI has no ~/.bittensor/wallets/default — generate ephemeral keys under a temp dir.
    with tempfile.TemporaryDirectory() as td:
        w = bt.Wallet(path=td, name="pytest_attest")
        w.create_new_coldkey(use_password=False, overwrite=True, suppress=True)
        w.create_new_hotkey(use_password=False, overwrite=True, suppress=True)
        s = LemmaChallenge(
            theorem_id="gen/1",
            theorem_statement="theorem t : True := by sorry",
            imports=["Mathlib"],
            lean_toolchain="lt",
            mathlib_rev="mr",
            deadline_unix=1,
            metronome_id="m99",
            deadline_block=None,
            proof_script="theorem x : True := rfl\n",
        )
        msg = miner_verify_attest_message(s)
        hx = sign_miner_verify_attest(w, msg)
        assert verify_miner_verify_attest_signature(
            hotkey_ss58=w.hotkey.ss58_address,
            message=msg,
            signature_hex=hx,
        )
        assert not verify_miner_verify_attest_signature(
            hotkey_ss58=w.hotkey.ss58_address,
            message=b"tampered",
            signature_hex=hx,
        )


def test_spot_verify_deterministic() -> None:
    a = attest_spot_should_full_verify(uid=3, theorem_id="t", metronome_id="m", spot_verify_fraction=0.5)
    b = attest_spot_should_full_verify(uid=3, theorem_id="t", metronome_id="m", spot_verify_fraction=0.5)
    assert a == b


def test_spot_verify_fraction_one_always_full() -> None:
    assert (
        attest_spot_should_full_verify(uid=1, theorem_id="a", metronome_id="b", spot_verify_fraction=1.0)
        is True
    )


def test_spot_verify_fraction_zero_never_full() -> None:
    assert (
        attest_spot_should_full_verify(uid=1, theorem_id="a", metronome_id="b", spot_verify_fraction=0.0)
        is False
    )
