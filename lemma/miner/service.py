"""Miner axon lifecycle."""

from __future__ import annotations

import time

import bittensor as bt
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.miner.forward import make_forward
from lemma.miner.gating import (
    MetagraphCache,
    make_miner_blacklist,
    make_miner_priority,
    zero_miner_priority,
)
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
        priority_fn = make_miner_priority(cache) if use_stake_priority else zero_miner_priority

        if s.lemma_miner_verify_attest_enabled and not s.miner_local_verify:
            raise SystemExit(
                "LEMMA_MINER_VERIFY_ATTEST_ENABLED=1 requires LEMMA_MINER_LOCAL_VERIFY=1 — "
                "miners must locally Lean-verify before signing attestations.",
            )
        prover = LLMProver(s)
        forward = make_forward(
            s,
            prover,
            metagraph_cache=cache,
            miner_hotkey_ss58=wallet.hotkey.ss58_address,
            wallet=wallet,
        )

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
        bits = [
            f"forward_timeline={'on' if s.miner_forward_timeline else 'off'}",
            f"local_lean_verify={'on' if s.miner_local_verify else 'off'}",
            f"log_forwards={'on' if s.miner_log_forwards else 'off'}",
            f"forward_summary={'on' if s.miner_forward_summary else 'off'}",
        ]
        logger.info("Miner visibility: {} (set in .env; `lemma miner observability` for detail)", "  ".join(bits))
        logger.info(
            "Per forward: my_uid / my_incentive at start; ends with miner answered (+ local_lean= if local verify on)."
        )
        logger.info("Miner running — Ctrl+C to stop.")
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
