"""Subtensor helpers."""

from __future__ import annotations

import bittensor as bt

from lemma.common.config import LemmaSettings


def get_subtensor(settings: LemmaSettings) -> bt.Subtensor:
    """Construct ``bt.Subtensor`` for SDK v10+ (no ``chain_endpoint`` kwarg).

    If ``SUBTENSOR_CHAIN_ENDPOINT`` is set, pass it as ``network`` so the SDK resolves the RPC.
    Otherwise use ``SUBTENSOR_NETWORK`` (e.g. ``test``, ``finney``).
    """
    endpoint = (settings.subtensor_chain_endpoint or "").strip()
    name = (settings.subtensor_network or "").strip()
    if endpoint:
        return bt.Subtensor(network=endpoint)
    if name:
        return bt.Subtensor(network=name)
    return bt.Subtensor()
