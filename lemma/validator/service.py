"""Validator metronome service."""

from __future__ import annotations

import asyncio
import os
import time

import bittensor as bt
from loguru import logger

from lemma.common.config import LemmaSettings, assert_validator_judge_stack_strict
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.factory import get_problem_source
from lemma.problems.generated import generated_registry_sha256
from lemma.validator import epoch as ep
from lemma.validator.protocol_migration import validate_protocol_feature_flags


def _require_docker_for_validator(settings: LemmaSettings) -> None:
    """Validators must use Docker for Lean — no host-lake escape hatch."""
    if settings.lean_use_docker:
        return
    raise SystemExit(
        "lemma validator requires Docker for Lean verify (LEMMA_USE_DOCKER=true).\n"
        "Host `lake` is not supported for validators — set LEMMA_USE_DOCKER=true in `.env`.",
    )


class ValidatorService:
    def __init__(self, settings: LemmaSettings | None = None, dry_run: bool | None = None) -> None:
        self.settings = settings or LemmaSettings()
        self.dry_run = dry_run if dry_run is not None else os.environ.get("LEMMA_DRY_RUN") == "1"

    async def run_forever(self) -> None:
        setup_logging(self.settings.log_level)
        logger.info(
            "Validator running — press Ctrl+C to stop and return to your shell.",
        )
        s = self.settings
        validate_protocol_feature_flags(s)
        _require_docker_for_validator(s)
        assert_validator_judge_stack_strict(s)
        if not (s.judge_profile_expected_sha256 or "").strip():
            raise SystemExit(
                "lemma validator requires JUDGE_PROFILE_SHA256_EXPECTED in `.env` "
                "(run `lemma configure subnet-pins` or copy from `lemma meta --raw`)."
            )
        if (s.problem_source or "").strip().lower() == "generated":
            if not (s.generated_registry_expected_sha256 or "").strip():
                raise SystemExit(
                    "lemma validator requires LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED when "
                    "LEMMA_PROBLEM_SOURCE=generated (run `lemma configure subnet-pins`)."
                )

        expected_raw = (s.judge_profile_expected_sha256 or "").strip()
        expected_j = expected_raw.lower()
        actual_judge = judge_profile_sha256(s).strip().lower()
        if actual_judge != expected_j:
            raise SystemExit(
                f"judge profile mismatch: expected JUDGE_PROFILE_SHA256_EXPECTED={expected_raw!r} "
                f"but current config hashes to {actual_judge!r}.\n"
                "Align judge env with the subnet, then run `lemma configure subnet-pins` "
                "(or set the pin to match `lemma meta` / `lemma meta --raw` manually)."
            )
        if (s.problem_source or "").strip().lower() == "generated":
            gr_actual = generated_registry_sha256()
            logger.info("generated_registry_sha256={}", gr_actual)
            gre = (s.generated_registry_expected_sha256 or "").strip()
            if gr_actual.strip().lower() != gre.lower():
                raise SystemExit(
                    f"generated registry mismatch: expected LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED={gre!r} "
                    f"but current code hashes to {gr_actual!r}.\n"
                    "Use the same lemma commit as the subnet, then `lemma configure subnet-pins` "
                    "(or update the registry pin from `lemma meta --raw`)."
                )
        subtensor = get_subtensor(s)
        source = get_problem_source(s)
        logger.info("problem_source={}", s.problem_source)
        logger.info(
            "validator cadence: subnet epoch boundaries only (each run_epoch waits for the next epoch)",
        )
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

    def run_blocking(self) -> None:
        import click

        from lemma.cli.style import finish_cli_output, stylize

        click.echo(
            stylize(
                "Validator running — press Ctrl+C to stop and return to your shell.",
                fg="cyan",
                bold=True,
            ),
            err=True,
        )
        try:
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            click.echo("")
            click.echo(
                stylize("Validator stopped (Ctrl+C).", fg="yellow", bold=True),
                err=True,
            )
        finally:
            finish_cli_output()


def wait_until_epoch(subtensor: bt.Subtensor, netuid: int, max_sleep: float = 7200.0) -> None:
    """Sleep until subnet epoch boundary (simple polling)."""
    t0 = time.monotonic()
    while time.monotonic() - t0 < max_sleep:
        bu = subtensor.blocks_until_next_epoch(netuid)
        if bu is not None and bu <= 1:
            return
        time.sleep(min(12.0, float(bu or 1) * 12.0))
