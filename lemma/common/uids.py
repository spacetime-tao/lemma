"""Metagraph UID helpers."""

from __future__ import annotations

import bittensor as bt


def axon_list_for_uids(metagraph: bt.Metagraph, uids: list[int]) -> list:
    """Return axon infos for the given UIDs in order."""
    return [metagraph.axons[uid] for uid in uids]
