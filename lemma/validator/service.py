"""Validator metronome service."""

from __future__ import annotations

import asyncio
import os
import time

import bittensor as bt
from loguru import logger

import lemma.validator.epoch as ep
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.subtensor import get_subtensor
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.factory import get_problem_source
from lemma.problems.generated import generated_registry_sha256
from lemma.validator.judge_profile_attest import judge_profile_peer_check_errors

_DOCKER_REQUIRED_ERROR = (
    "lemma validator requires Docker for Lean verify (LEMMA_USE_DOCKER=true).\n"
    "Host `lake` is not supported for validators — set LEMMA_USE_DOCKER=true in `.env`."
)


def epoch_sleep_seconds(blocks_until_epoch: int, block_time_sec_estimate: float) -> float:
    """Poll near epoch boundaries instead of trusting rough wall-clock estimates."""
    bu = int(blocks_until_epoch)
    if bu <= 1:
        return 0.0
    if bu <= 3:
        return 1.0
    return min(12.0, max(1.0, float(bu) * float(block_time_sec_estimate) * 0.25))


def _require_docker_for_validator(settings: LemmaSettings) -> None:
    """Validators must use Docker for Lean — no host-lake escape hatch."""
    if settings.lean_use_docker:
        return
    raise SystemExit(_DOCKER_REQUIRED_ERROR)


def validator_startup_issues(settings: LemmaSettings, *, dry_run: bool) -> tuple[list[str], list[str]]:
    """Consensus-critical gates shared by `validator start` and `validator-check`."""
    fatal: list[str] = []
    warn: list[str] = []

    if not settings.lean_use_docker:
        fatal.append(_DOCKER_REQUIRED_ERROR)

    if not (settings.judge_profile_expected_sha256 or "").strip():
        fatal.append(
            "lemma validator requires JUDGE_PROFILE_SHA256_EXPECTED in `.env` "
            "(run `lemma-cli configure subnet-pins` or copy from `lemma meta --raw`).",
        )
    else:
        expected_raw = (settings.judge_profile_expected_sha256 or "").strip()
        actual_judge = judge_profile_sha256(settings).strip().lower()
        if actual_judge != expected_raw.lower():
            fatal.append(
                f"validator profile mismatch: expected JUDGE_PROFILE_SHA256_EXPECTED={expected_raw!r} "
                f"but current config hashes to {actual_judge!r}.\n"
                "Align validator profile env with the subnet, then run `lemma-cli configure subnet-pins` "
                "(or set the pin to match `lemma meta` / `lemma meta --raw` manually).",
            )

    problem_source = (settings.problem_source or "").strip().lower()
    if problem_source == "generated":
        if not (settings.generated_registry_expected_sha256 or "").strip():
            fatal.append(
                "lemma validator requires LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED when "
                "LEMMA_PROBLEM_SOURCE=generated (run `lemma-cli configure subnet-pins`).",
            )
        else:
            gr_actual = generated_registry_sha256()
            gre = (settings.generated_registry_expected_sha256 or "").strip()
            if gr_actual.strip().lower() != gre.lower():
                fatal.append(
                    f"generated registry mismatch: expected LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED={gre!r} "
                    f"but current code hashes to {gr_actual!r}.\n"
                    "Use the same lemma commit as the subnet, then `lemma-cli configure subnet-pins` "
                    "(or update the registry pin from `lemma meta --raw`).",
                )
    elif problem_source == "frozen" and not settings.lemma_dev_allow_frozen_problem_source:
        fatal.append(
            "LEMMA_PROBLEM_SOURCE=frozen requires LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1 "
            "(public eval catalog). Use generated for subnet traffic — see docs/catalog-sources.md",
        )

    if settings.lemma_judge_profile_attest_enabled and settings.lemma_judge_profile_attest_allow_skip:
        warn.append(
            "LEMMA_JUDGE_PROFILE_ATTEST_SKIP=1 — peer validator profile HTTP checks skipped "
            "(solo / dev only; not production alignment)",
        )
    fatal.extend(judge_profile_peer_check_errors(settings))

    return fatal, warn


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
        fatal, warn = await asyncio.to_thread(validator_startup_issues, s, dry_run=self.dry_run)
        for msg in warn:
            logger.warning(msg)
        if fatal:
            raise SystemExit(fatal[0])
        if (s.problem_source or "").strip().lower() == "generated":
            logger.info("generated_registry_sha256={}", generated_registry_sha256())
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
            wait_s = epoch_sleep_seconds(bu, s.block_time_sec_estimate)
            logger.debug("Waiting {:.0f}s (~{} blocks to epoch)", wait_s, bu)
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
