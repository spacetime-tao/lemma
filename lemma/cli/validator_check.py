"""Validator preflight for the proof-only trunk."""

from __future__ import annotations

import click

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings
from lemma.problems.known_theorems import known_theorems_manifest_sha256
from lemma.validator.profile import validator_profile_sha256
from lemma.validator.service import validator_startup_issues


def run_validator_check(settings: LemmaSettings | None = None) -> int:
    settings = settings or LemmaSettings()
    fatal, warn = validator_startup_issues(settings, dry_run=True)
    click.echo(stylize("Lemma validator check", fg="cyan", bold=True))
    click.echo(f"problem_source={settings.problem_source}")
    click.echo(f"cadence_window_blocks={settings.cadence_window_blocks}")
    click.echo(f"uid_variant_problems={settings.lemma_uid_variant_problems}")
    click.echo(f"known_theorems_manifest_sha256={known_theorems_manifest_sha256(settings.known_theorems_manifest_path)}")
    click.echo(f"validator_profile_sha256={validator_profile_sha256(settings)}")
    for msg in warn:
        click.echo(stylize("WARN ", fg="yellow", bold=True) + msg)
    for msg in fatal:
        click.echo(stylize("FAIL ", fg="red", bold=True) + msg)
    if fatal:
        return 2
    click.echo(stylize("READY", fg="green", bold=True))
    return 0
