"""Payload size limits for incoming synapses."""

from __future__ import annotations

from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge
from lemma.protocol_commit_reveal import looks_like_commitment_hex


def synapse_payload_error(
    synapse: LemmaChallenge,
    settings: LemmaSettings,
    *,
    response: bool = True,
) -> str | None:
    """Return an error message if challenge/response fields exceed configured caps."""
    stmt = synapse.theorem_statement or ""
    if len(stmt) > settings.synapse_max_statement_chars:
        return "theorem_statement too large"
    if not response:
        return None
    phase = (synapse.commit_reveal_phase or "off").strip().lower()
    pc = (synapse.proof_commitment_hex or "").strip()
    if phase == "commit" and pc:
        if not looks_like_commitment_hex(pc):
            return "proof_commitment_hex must be 64 hex chars, with optional 0x prefix"
        if (synapse.proof_script or "").strip():
            return "commit phase response must not include proof_script"
        return None
    pr = synapse.proof_script or ""
    if len(pr) > settings.synapse_max_proof_chars:
        return "proof_script too large"
    return None


def reject_synopsis(synapse: LemmaChallenge, status: int, message: str) -> LemmaChallenge:
    """Mark synapse as failed without running the prover."""
    if synapse.axon is not None:
        synapse.axon.status_code = status
        synapse.axon.status_message = message
    synapse.proof_script = None
    return synapse
