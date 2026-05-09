"""Commit–reveal preimage consistency."""

from lemma.protocol_commit_reveal import (
    commit_preimage_v1,
    commitment_hex_from_preimage,
    looks_like_commitment_hex,
    normalize_commitment_hex,
    reasoning_blob_for_commit,
    verify_reveal_against_commitment,
)


def test_commit_reveal_roundtrip() -> None:
    nonce = bytes(range(32))
    proof = "namespace Submission\n theorem t : True := rfl\n"
    rb = reasoning_blob_for_commit("hello", None)
    pre = commit_preimage_v1(
        theorem_id="gen/1",
        metronome_id="42",
        nonce=nonce,
        proof_script=proof,
        reasoning_blob=rb,
    )
    ch = commitment_hex_from_preimage(pre)
    assert verify_reveal_against_commitment(
        expected_commitment_hex=ch,
        theorem_id="gen/1",
        metronome_id="42",
        nonce_hex=nonce.hex(),
        proof_script=proof,
        reasoning_blob=rb,
    )
    assert not verify_reveal_against_commitment(
        expected_commitment_hex=ch,
        theorem_id="gen/1",
        metronome_id="42",
        nonce_hex=nonce.hex(),
        proof_script=proof + "\n",
        reasoning_blob=rb,
    )


def test_commitment_hex_accepts_optional_0x_prefix() -> None:
    nonce = bytes(range(32))
    proof = "namespace Submission\n theorem t : True := rfl\n"
    rb = reasoning_blob_for_commit("hello", None)
    pre = commit_preimage_v1(
        theorem_id="gen/1",
        metronome_id="42",
        nonce=nonce,
        proof_script=proof,
        reasoning_blob=rb,
    )
    ch = commitment_hex_from_preimage(pre)

    assert looks_like_commitment_hex("0x" + ch)
    assert normalize_commitment_hex("0X" + ch.upper()) == ch
    assert verify_reveal_against_commitment(
        expected_commitment_hex="0x" + ch,
        theorem_id="gen/1",
        metronome_id="42",
        nonce_hex="0x" + nonce.hex(),
        proof_script=proof,
        reasoning_blob=rb,
    )
