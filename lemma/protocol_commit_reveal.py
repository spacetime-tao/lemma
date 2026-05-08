"""Commit–reveal for miner responses (optional ``LEMMA_COMMIT_REVEAL_ENABLED``).

Phase ``commit``: miner sends ``proof_commitment_hex = SHA256(preimage)`` without revealing proof text.
Phase ``reveal``: miner sends full proof, reasoning, and ``commit_reveal_nonce_hex``; validator checks
the preimage matches the stored commitment from phase ``commit``.
"""

from __future__ import annotations

import hashlib
import json
import re

_MAGIC = b"LemmaCommitRevealV1"


def reasoning_blob_for_commit(trace: str | None, steps: list | None) -> str:
    """Canonical string for hashing (must match miner commit and validator verify)."""
    if steps:
        ser = []
        for st in steps:
            title = getattr(st, "title", None)
            text = getattr(st, "text", "") or ""
            ser.append([title, text])
        return json.dumps(ser, sort_keys=True)
    return trace or ""


def commit_preimage_v1(
    *,
    theorem_id: str,
    metronome_id: str,
    nonce: bytes,
    proof_script: str,
    reasoning_blob: str,
) -> bytes:
    if len(nonce) != 32:
        raise ValueError("nonce must be 32 bytes")
    parts = (
        _MAGIC,
        (theorem_id or "").encode("utf-8"),
        (metronome_id or "").encode("utf-8"),
        nonce,
        (proof_script or "").encode("utf-8"),
        (reasoning_blob or "").encode("utf-8"),
    )
    return b"\x1e".join(parts)


def commitment_hex_from_preimage(preimage: bytes) -> str:
    return hashlib.sha256(preimage).hexdigest()


def verify_reveal_against_commitment(
    *,
    expected_commitment_hex: str,
    theorem_id: str,
    metronome_id: str,
    nonce_hex: str,
    proof_script: str,
    reasoning_blob: str,
) -> bool:
    raw = (nonce_hex or "").strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) != 64:
        return False
    try:
        nonce = bytes.fromhex(raw)
    except ValueError:
        return False
    if len(nonce) != 32:
        return False
    try:
        pre = commit_preimage_v1(
            theorem_id=theorem_id,
            metronome_id=metronome_id,
            nonce=nonce,
            proof_script=proof_script,
            reasoning_blob=reasoning_blob,
        )
    except ValueError:
        return False
    digest = commitment_hex_from_preimage(pre).lower()
    exp = (expected_commitment_hex or "").strip().lower()
    if exp.startswith("0x"):
        exp = exp[2:]
    return digest == exp


_COMMIT_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def looks_like_commitment_hex(s: str | None) -> bool:
    return bool(s and _COMMIT_HEX_RE.match(s.strip()))
