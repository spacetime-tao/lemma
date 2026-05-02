"""Validator metronome service."""

from __future__ import annotations

import asyncio
import os
import time

import bittensor as bt
from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.factory import get_problem_source
from lemma.problems.generated import generated_registry_sha256
from lemma.validator import epoch as ep


class ValidatorService:
    def __init__(self, settings: LemmaSettings | None = None, dry_run: bool | None = None) -> None:
        self.settings = settings or LemmaSettings()
        self.dry_run = dry_run if dry_run is not None else os.environ.get("LEMMA_DRY_RUN") == "1"

    async def run_forever(self) -> None:
        setup_logging(self.settings.log_level)
        s = self.settings
        expected = s.judge_profile_expected_sha256
        if expected:
            actual = judge_profile_sha256(s)
            if actual != expected.strip().lower():
                raise SystemExit(
                    f"judge profile mismatch: expected JUDGE_PROFILE_SHA256_EXPECTED={expected!r} "
                    f"but current config hashes to {actual!r}. Run `lemma meta` and align env."
                )
        if (s.problem_source or "").strip().lower() == "generated":
            gr_actual = generated_registry_sha256()
            logger.info("generated_registry_sha256={}", gr_actual)
            gre = s.generated_registry_expected_sha256
            if gre and gr_actual != gre.strip().lower():
                raise SystemExit(
                    f"generated registry mismatch: expected LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED={gre!r} "
                    f"but current code hashes to {gr_actual!r}. Run `lemma meta` and align release/git tag."
                )
        subtensor = get_subtensor(s)
        source = get_problem_source(s)
        logger.info("problem_source={}", s.problem_source)
        if s.validator_align_rounds_to_epoch:
            logger.info("validator rounds aligned to chain epochs (LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH=1)")
            while True:
                bu = subtensor.blocks_until_next_epoch(s.netuid)
                if bu is None:
                    await asyncio.sleep(12)
                    continue
                if bu <= 1:
                    try:
                        await ep.run_epoch(s, source, dry_run=self.dry_run)
                    except Exception as e:  # noqa: BLE001
                        logger.exception("epoch failed: {}", e)
                    await asyncio.sleep(2)
                    continue
                wait_s = min(float(bu) * 12.0, 600.0)
                logger.info("Sleeping {:.0f}s (~{} blocks to epoch)", wait_s, bu)
                await asyncio.sleep(wait_s)
        else:
            interval = float(s.validator_round_interval_s)
            logger.info(
                "validator rounds every {:.0f}s (LEMMA_VALIDATOR_ROUND_INTERVAL_S); not waiting for epoch",
                interval,
            )
            while True:
                try:
                    await ep.run_epoch(s, source, dry_run=self.dry_run)
                except Exception as e:  # noqa: BLE001
                    logger.exception("round failed: {}", e)
                await asyncio.sleep(interval)

    def run_blocking(self) -> None:
        asyncio.run(self.run_forever())


def wait_until_epoch(subtensor: bt.Subtensor, netuid: int, max_sleep: float = 7200.0) -> None:
    """Sleep until subnet epoch boundary (simple polling)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < max_sleep:
        bu = subtensor.blocks_until_next_epoch(netuid)
        if bu is not None and bu <= 1:
            return
        time.sleep(min(12.0, float(bu or 1) * 12.0))
