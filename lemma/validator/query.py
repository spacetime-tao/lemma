"""Dendrite query helpers."""

from __future__ import annotations

import bittensor as bt

from lemma.protocol import LemmaChallenge


async def query_miners(
    dendrite: bt.Dendrite,
    axons: list,
    synapse: LemmaChallenge,
    timeout: float,
) -> list:
    """Forward synapse to all axons; returns list of synapse responses (order preserved)."""
    return await dendrite(axons, synapse, timeout=timeout, run_async=True)
