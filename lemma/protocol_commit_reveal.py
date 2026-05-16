"""Commit–reveal for miner responses (optional ``LEMMA_COMMIT_REVEAL_ENABLED``).

Phase ``commit``: miner sends ``proof_commitment_hex = SHA256(preimage)`` without revealing proof text.
Phase ``reveal``: miner sends full proof and ``commit_reveal_nonce_hex``; validator checks
the preimage matches the stored commitment from phase ``commit``.
"""

from __future__ import annotations

import hashlib
import re

_MAGIC = b"LemmaCommitRevealV1"
_NONCE_HEX_CHARS = 64
_COMMIT_HEX_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _strip_hex_prefix(s: str | None) -> str:
    raw = (s or "").strip()
    if raw.lower().startswith("0x"):
        return raw[2:]
    return raw


def _bytes_from_fixed_hex(s: str | None, *, hex_chars: int) -> bytes | None:
    raw = _strip_hex_prefix(s)
    if len(raw) != hex_chars:
        return None
    try:
        return bytes.fromhex(raw)
    except ValueError:
        return None


def commit_preimage_v1(
    *,
    theorem_id: str,
    metronome_id: str,
    nonce: bytes,
    proof_script: str,
) -> bytes:
    if len(nonce) != 32:
        raise ValueError("nonce must be 32 bytes")
    parts = (
        _MAGIC,
        (theorem_id or "").encode("utf-8"),
        (metronome_id or "").encode("utf-8"),
        nonce,
        (proof_script or "").encode("utf-8"),
    )
    return b"\x1e".join(parts)


def commitment_hex_from_preimage(preimage: bytes) -> str:
    return hashlib.sha256(preimage).hexdigest()


def normalize_commitment_hex(s: str | None) -> str | None:
    """Return lowercase commitment hex, accepting an optional ``0x`` prefix."""
    raw = _strip_hex_prefix(s)
    if not _COMMIT_HEX_RE.fullmatch(raw):
        return None
    return raw.lower()


def verify_reveal_against_commitment(
    *,
    expected_commitment_hex: str,
    theorem_id: str,
    metronome_id: str,
    nonce_hex: str,
    proof_script: str,
) -> bool:
    nonce = _bytes_from_fixed_hex(nonce_hex, hex_chars=_NONCE_HEX_CHARS)
    if nonce is None:
        return False
    try:
        pre = commit_preimage_v1(
            theorem_id=theorem_id,
            metronome_id=metronome_id,
            nonce=nonce,
            proof_script=proof_script,
        )
    except ValueError:
        return False
    digest = commitment_hex_from_preimage(pre).lower()
    exp = normalize_commitment_hex(expected_commitment_hex)
    if exp is None:
        return False
    return digest == exp


def looks_like_commitment_hex(s: str | None) -> bool:
    return normalize_commitment_hex(s) is not None
