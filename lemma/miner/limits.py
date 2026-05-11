"""Miner helpers for rejecting synapses."""

from __future__ import annotations

from lemma.protocol import LemmaChallenge


def reject_synopsis(synapse: LemmaChallenge, status: int, message: str) -> LemmaChallenge:
    """Mark synapse as failed without running the prover."""
    if synapse.axon is not None:
        synapse.axon.status_code = status
        synapse.axon.status_message = message
    synapse.proof_script = None
    return synapse
