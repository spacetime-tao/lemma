"""Manual-proof miner axon lifecycle."""

from __future__ import annotations

import time
from typing import Tuple  # noqa: UP035

import bittensor as bt
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.common.synapse_limits import synapse_payload_error
from lemma.miner.forward import make_forward
from lemma.protocol import LemmaChallenge
from lemma.submissions import load_pending_submissions, resolved_submissions_path


def _miner_blacklist(settings: LemmaSettings):
    def blacklist(synapse: LemmaChallenge) -> Tuple[bool, str]:  # noqa: UP006
        err = synapse_payload_error(synapse, settings, response=False)
        return (err is not None, err or "")

    return blacklist


def _zero_priority(synapse: LemmaChallenge) -> float:
    return 0.0


class MinerService:
    def __init__(self, settings: LemmaSettings | None = None) -> None:
        self.settings = settings or LemmaSettings()

    def run(self) -> None:
        setup_logging(self.settings.log_level)
        s = self.settings
        wallet = bt.Wallet(name=s.wallet_cold, hotkey=s.wallet_hot)
        subtensor = get_subtensor(s)

        external_ip = (s.axon_external_ip or "").strip() or None
        if external_ip is None:
            logger.warning("AXON_EXTERNAL_IP is unset; set it explicitly if validators cannot reach this miner")

        axon = bt.Axon(wallet=wallet, port=s.axon_port, external_ip=external_ip)
        axon.attach(forward_fn=make_forward(s), blacklist_fn=_miner_blacklist(s), priority_fn=_zero_priority)
        axon.serve(netuid=s.netuid, subtensor=subtensor)
        axon.start()

        pending = load_pending_submissions(s.miner_submissions_path)
        logger.info(
            "Manual-proof miner listening netuid={} port={} hotkey={} submissions={} store={}",
            s.netuid,
            s.axon_port,
            wallet.hotkey.ss58_address,
            len(pending),
            resolved_submissions_path(s.miner_submissions_path),
        )
        logger.info("Miner running - Ctrl+C to stop.")
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Miner shutting down")
            axon.stop()
