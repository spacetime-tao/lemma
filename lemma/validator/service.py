"""Validator polling service for manual-proof WTA."""

from __future__ import annotations

import asyncio
import os

from loguru import logger

import lemma.validator.epoch as ep
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import get_problem_source
from lemma.problems.known_theorems import known_theorems_manifest_sha256
from lemma.validator.profile import validator_profile_sha256

_DOCKER_REQUIRED_ERROR = (
    "lemma validator requires Docker for Lean verify (LEMMA_USE_DOCKER=true).\n"
    "Host `lake` is allowed only for local `lemma verify --host-lean`."
)


def validator_startup_issues(settings: LemmaSettings, *, dry_run: bool) -> tuple[list[str], list[str]]:
    fatal: list[str] = []
    warn: list[str] = []
    if not settings.lean_use_docker:
        fatal.append(_DOCKER_REQUIRED_ERROR)

    expected_profile = (settings.validator_profile_expected_sha256 or "").strip()
    if not expected_profile:
        fatal.append(
            "lemma validator requires LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED "
            "(copy validator_profile_sha256 from `lemma meta --raw`).",
        )
    else:
        actual = validator_profile_sha256(settings)
        if actual.lower() != expected_profile.lower():
            fatal.append(
                "validator profile mismatch: expected "
                f"LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED={expected_profile!r} "
                f"but current config hashes to {actual!r}.",
            )

    expected_manifest = (settings.known_theorems_manifest_expected_sha256 or "").strip()
    if not expected_manifest:
        fatal.append(
            "lemma validator requires LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED "
            "(copy known_theorems_manifest_sha256 from `lemma meta --raw`).",
        )
    else:
        actual_manifest = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
        if actual_manifest.lower() != expected_manifest.lower():
            fatal.append(
                "known-theorem manifest mismatch: expected "
                f"LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED={expected_manifest!r} "
                f"but current manifest hashes to {actual_manifest!r}.",
            )

    return fatal, warn


class ValidatorService:
    def __init__(self, settings: LemmaSettings | None = None, dry_run: bool | None = None) -> None:
        self.settings = settings or LemmaSettings()
        self.dry_run = dry_run if dry_run is not None else os.environ.get("LEMMA_DRY_RUN") == "1"

    async def run_forever(self) -> None:
        setup_logging(self.settings.log_level)
        s = self.settings
        fatal, warn = await asyncio.to_thread(validator_startup_issues, s, dry_run=self.dry_run)
        for msg in warn:
            logger.warning(msg)
        if fatal:
            raise SystemExit(fatal[0])

        logger.info("known_theorems_manifest_sha256={}", known_theorems_manifest_sha256(s.known_theorems_manifest_path))
        logger.info("validator_profile_sha256={}", validator_profile_sha256(s))
        logger.info("validator poll interval={}s", s.validator_poll_interval_s)
        source = get_problem_source(s)
        while True:
            try:
                await ep.run_epoch(s, source, dry_run=self.dry_run)
                await asyncio.sleep(float(s.validator_poll_interval_s))
            except Exception as exc:  # noqa: BLE001
                logger.exception("validator poll failed; retrying after interval: {}", exc)
                await asyncio.sleep(float(s.validator_poll_interval_s))

    def run_blocking(self) -> None:
        import click

        from lemma.cli.style import finish_cli_output, stylize

        click.echo(stylize("Validator running - press Ctrl+C to stop.", fg="cyan", bold=True), err=True)
        try:
            asyncio.run(self.run_forever())
        except KeyboardInterrupt:
            click.echo("")
            click.echo(stylize("Validator stopped (Ctrl+C).", fg="yellow", bold=True), err=True)
        finally:
            finish_cli_output()
