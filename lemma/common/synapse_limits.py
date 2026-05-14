"""Payload size limits for Lemma challenge and response synapses."""

from __future__ import annotations

from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge


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
    pr = synapse.proof_script or ""
    if len(pr) > settings.synapse_max_proof_chars:
        return "proof_script too large"
    return None
