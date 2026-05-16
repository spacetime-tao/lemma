"""Miner Lean-verify attestation (Sr25519 hotkey signatures).

When ``LEMMA_MINER_VERIFY_ATTEST_ENABLED=1``, miners sign a canonical preimage binding
the validator hotkey, ``theorem_id``, ``metronome_id``, toolchain pins, and
``SHA256(proof_script)``. Validators verify the signature against the metagraph hotkey
for that UID.
"""

from __future__ import annotations

import hashlib

import bittensor as bt

from lemma.protocol import LemmaChallenge

_ATTEST_MAGIC = b"LemmaMinerVerifyAttestV2"


def miner_verify_attest_message(s: LemmaChallenge, *, validator_hotkey: str) -> bytes:
    """Return the byte message the miner hotkey must sign (challenge + proof binding)."""
    vh = str(validator_hotkey or "").strip()
    if not vh:
        raise ValueError("validator_hotkey is required for miner verify attest")
    proof = (s.proof_script or "").encode("utf-8")
    proof_digest = hashlib.sha256(proof).digest()
    parts = (
        _ATTEST_MAGIC,
        vh.encode("utf-8"),
        (s.theorem_id or "").encode("utf-8"),
        (s.metronome_id or "").encode("utf-8"),
        (s.lean_toolchain or "").encode("utf-8"),
        (s.mathlib_rev or "").encode("utf-8"),
        proof_digest,
    )
    return b"\x1e".join(parts)


def sign_miner_verify_attest(wallet: bt.Wallet, message: bytes) -> str:
    """Return hex-encoded Sr25519 signature (64 bytes)."""
    sig = wallet.hotkey.sign(message)
    return sig.hex()


def verify_miner_verify_attest_signature(*, hotkey_ss58: str, message: bytes, signature_hex: str) -> bool:
    """Verify ``signature_hex`` was produced by ``hotkey_ss58`` over ``message``."""
    raw = (signature_hex or "").strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) != 128:
        return False
    try:
        sig = bytes.fromhex(raw)
    except ValueError:
        return False
    kp = bt.Keypair(ss58_address=hotkey_ss58)
    return bool(kp.verify(message, sig))


def attest_spot_should_full_verify(
    *,
    uid: int,
    theorem_id: str,
    metronome_id: str,
    spot_verify_fraction: float,
    spot_verify_salt: str = "",
) -> bool:
    """Deterministic per (uid, theorem, round): whether this response runs full Lean verify.

    ``spot_verify_fraction`` in ``[0, 1]``: fraction of tuples selected for full verify.
    ``1.0`` = always verify; ``0.0`` = never verify (trust attest only — dangerous).
    ``spot_verify_salt`` makes the selected subset less predictable before the salt is known.
    """
    fv = max(0.0, min(1.0, float(spot_verify_fraction)))
    if fv >= 1.0:
        return True
    if fv <= 0.0:
        return False
    h = hashlib.sha256(f"{spot_verify_salt}\n{uid}\n{theorem_id}\n{metronome_id}".encode()).digest()
    x = int.from_bytes(h[:8], "big") / float(2**64)
    return x < fv
