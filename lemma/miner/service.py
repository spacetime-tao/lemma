"""Miner axon lifecycle."""

from __future__ import annotations

import time

import bittensor as bt
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.miner.forward import make_forward, priority_stub
from lemma.miner.gating import MetagraphCache, make_miner_blacklist, make_miner_priority
from lemma.miner.prover import LLMProver
from lemma.miner.public_ip import discover_public_ipv4


class MinerService:
    def __init__(self, settings: LemmaSettings | None = None) -> None:
        self.settings = settings or LemmaSettings()

    def run(self) -> None:
        setup_logging(self.settings.log_level)
        s = self.settings
        wallet = bt.Wallet(name=s.wallet_cold, hotkey=s.wallet_hot)
        subtensor = get_subtensor(s)
        cache = MetagraphCache(subtensor, s.netuid, refresh_s=s.miner_metagraph_refresh_s)
        blacklist_fn = make_miner_blacklist(s, cache)
        use_stake_priority = (
            s.miner_priority_by_stake
            or s.miner_min_validator_stake > 0.0
            or s.miner_require_validator_permit
        )
        priority_fn = make_miner_priority(cache) if use_stake_priority else priority_stub

        prover = LLMProver(s)
        forward = make_forward(s, prover)

        external_ip = (s.axon_external_ip or "").strip() or None
        if external_ip is None and s.axon_discover_external_ip:
            discovered = discover_public_ipv4()
            if discovered:
                external_ip = discovered
                logger.info(
                    "axon external_ip={} (auto-discovered; set AXON_EXTERNAL_IP to override)",
                    external_ip,
                )
            else:
                logger.warning(
                    "could not auto-discover public IP — set AXON_EXTERNAL_IP or open port {}",
                    s.axon_port,
                )
        elif external_ip is not None:
            logger.info("axon external_ip={} (from AXON_EXTERNAL_IP)", external_ip)

        axon = bt.Axon(
            wallet=wallet,
            port=s.axon_port,
            external_ip=external_ip,
        )
        axon.attach(
            forward_fn=forward,
            blacklist_fn=blacklist_fn,
            priority_fn=priority_fn,
        )
        axon.serve(netuid=s.netuid, subtensor=subtensor)
        axon.start()
        logger.info(
            "Miner axon listening netuid={} port={} hotkey={}",
            s.netuid,
            s.axon_port,
            wallet.hotkey.ss58_address,
        )
        logger.info(
            "Miner running — press Ctrl+C to stop and return to your shell.",
        )
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            logger.info("Miner shutting down")
            axon.stop()
            import click

            from lemma.cli.style import finish_cli_output, stylize

            click.echo("")
            click.echo(stylize("Miner stopped (Ctrl+C).", fg="yellow", bold=True), err=True)
            finish_cli_output()
