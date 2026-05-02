"""Payload size limits for incoming synapses."""

from __future__ import annotations

from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge


def _reasoning_payload_len(synapse: LemmaChallenge) -> int:
    steps = synapse.reasoning_steps
    if steps:
        return sum(len(s.text) + len(s.title or "") for s in steps)
    return len(synapse.reasoning_trace or "")


def synapse_payload_error(synapse: LemmaChallenge, settings: LemmaSettings) -> str | None:
    """Return an error message if challenge fields exceed configured caps."""
    stmt = synapse.theorem_statement or ""
    if len(stmt) > settings.synapse_max_statement_chars:
        return "theorem_statement too large"
    if _reasoning_payload_len(synapse) > settings.synapse_max_trace_chars:
        return "reasoning_trace or reasoning_steps too large"
    pr = synapse.proof_script or ""
    if len(pr) > settings.synapse_max_proof_chars:
        return "proof_script too large"
    return None


def reject_synopsis(synapse: LemmaChallenge, status: int, message: str) -> LemmaChallenge:
    """Mark synapse as failed without running the prover."""
    if synapse.axon is not None:
        synapse.axon.status_code = status
        synapse.axon.status_message = message
    synapse.reasoning_trace = None
    synapse.reasoning_steps = None
    synapse.proof_script = None
    return synapse
