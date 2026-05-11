"""Blacklist / priority using metagraph stake (optional production gate)."""

import time
from typing import Any, Tuple, cast  # noqa: UP035 — Axon signature check expects ``typing.Tuple``, not ``tuple``

import bittensor as bt
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.protocol import LemmaChallenge


class MetagraphCache:
    """Lazy-refreshed metagraph for miner-side policy."""

    def __init__(
        self,
        subtensor: bt.Subtensor,
        netuid: int,
        *,
        refresh_s: float,
    ) -> None:
        self._subtensor = subtensor
        self._netuid = netuid
        self._refresh_s = refresh_s
        self._mg: bt.Metagraph | None = None
        self._last_refresh = 0.0

    def get(self) -> bt.Metagraph:
        now = time.monotonic()
        if self._mg is None or (now - self._last_refresh) >= self._refresh_s:
            self._mg = self._subtensor.metagraph(self._netuid)
            self._last_refresh = now
            logger.debug("miner metagraph refreshed netuid={}", self._netuid)
        return self._mg


def metagraph_incentive_for_hotkey(
    cache: MetagraphCache,
    hotkey_ss58: str,
) -> tuple[int | None, float | None]:
    """Your subnet UID and incentive column from the cached Bittensor metagraph."""
    mg = cache.get()
    uid = _uid_for_hotkey(mg, hotkey_ss58)
    if uid is None:
        return None, None
    if not hasattr(mg, "I"):
        return uid, None
    raw = mg.I[uid]
    try:
        inc = float(cast(Any, raw).item())
    except Exception:
        inc = float(raw)
    return uid, inc


def _uid_for_hotkey(metagraph: bt.Metagraph, hotkey: str) -> int | None:
    for uid, hk in enumerate(metagraph.hotkeys):
        if hk == hotkey:
            return uid
    return None


def _float_stake(metagraph: bt.Metagraph, uid: int) -> float:
    raw = metagraph.S[uid]
    try:
        return float(cast(Any, raw).item())
    except Exception:
        return float(raw)


def _bool_tensor(metagraph: bt.Metagraph, name: str, uid: int) -> bool:
    tensor = getattr(metagraph, name)
    try:
        v = tensor[uid]
        return bool(cast(Any, v).item())
    except Exception:
        return bool(v)


def make_miner_blacklist(settings: LemmaSettings, cache: MetagraphCache):
    def blacklist(synapse: LemmaChallenge) -> Tuple[bool, str]:  # noqa: UP006
        from lemma.common.synapse_limits import synapse_payload_error

        pay_err = synapse_payload_error(synapse, settings, response=False)
        if pay_err:
            return True, pay_err

        if settings.miner_min_validator_stake <= 0.0 and not settings.miner_require_validator_permit:
            return False, ""

        if synapse.dendrite is None or not synapse.dendrite.hotkey:
            return True, "missing dendrite hotkey"

        mg = cache.get()
        hk = synapse.dendrite.hotkey
        uid = _uid_for_hotkey(mg, hk)
        if uid is None:
            return True, "hotkey not in metagraph"

        if settings.miner_require_validator_permit and not _bool_tensor(mg, "validator_permit", uid):
            return True, "validator_permit false"

        if settings.miner_min_validator_stake > 0.0:
            stake = _float_stake(mg, uid)
            if stake < settings.miner_min_validator_stake:
                return True, "below miner_min_validator_stake"

        return False, ""

    return blacklist


def zero_miner_priority(synapse: LemmaChallenge) -> float:
    return 0.0


def make_miner_priority(cache: MetagraphCache):
    def priority(synapse: LemmaChallenge) -> float:
        if synapse.dendrite is None or not synapse.dendrite.hotkey:
            return 0.0
        mg = cache.get()
        uid = _uid_for_hotkey(mg, synapse.dendrite.hotkey)
        if uid is None:
            return 0.0
        return _float_stake(mg, uid)

    return priority
