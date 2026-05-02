"""START HERE onboarding screen for `lemma` / `lemma start`."""

from __future__ import annotations

import sys

import click


def show_start_here(ctx: click.Context | None = None, *, group: click.Group | None = None) -> None:
    """Print the onboarding roadmap and optionally branch into another command."""
    click.echo(
        """
 ======================================================================
   Lemma — START HERE
 ======================================================================

   New install (from repo root):

     uv sync --extra dev
     lemma

   Or: activate .venv, run `lemma setup` when prompted.

 ----------------------------------------------------------------------
   Reference: docs/GETTING_STARTED.md
 ----------------------------------------------------------------------
   uv sync --extra dev
   lemma setup              (prompts → .env)
   btcli                    coldkey / hotkey, then subnet register
   lemma miner | lemma validator

   Same sampling as validators:  lemma status
                                   lemma problems show --current

   lemma doctor | lemma docs

 ----------------------------------------------------------------------
   Defaults
 ----------------------------------------------------------------------
   Time limits: subnet operator publishes DENDRITE_TIMEOUT_S / LEAN_VERIFY_TIMEOUT_S (defaults
   often 300 s each). Everyone runs the same policy (see docs/FAQ.md, GOVERNANCE.md).

   Theorem seed: LEMMA_PROBLEM_SEED_MODE=subnet_epoch (default) or quantize.

   Rounds: LEMMA_VALIDATOR_ROUND_INTERVAL_S (timer), unless
   LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH=1.

 ======================================================================
"""
    )

    if ctx is None or group is None or not sys.stdin.isatty():
        click.echo("Tip: run `lemma start` for this menu. Next: `lemma setup`")
        return

    choice = click.prompt(
        "Next step",
        type=click.Choice(
            [
                "setup",
                "doctor",
                "docs",
                "status",
                "miner-dry",
                "validator-dry",
                "meta",
                "quit",
            ],
            case_sensitive=False,
        ),
        default="setup",
        show_default=True,
    )
    key = choice.lower()
    if key == "quit":
        return

    spec: dict[str, tuple[str, dict[str, object]]] = {
        "setup": ("setup", {}),
        "doctor": ("doctor", {}),
        "docs": ("docs", {}),
        "status": ("status", {}),
        "miner-dry": ("miner", {"dry_run": True}),
        "validator-dry": ("validator", {"dry_run": True}),
        "meta": ("meta", {}),
    }
    if key not in spec:
        return
    name, kwargs = spec[key]
    cmd = group.get_command(ctx, name)
    if cmd is None:
        click.echo(f"Command {name!r} not found.", err=True)
        return
    ctx.invoke(cmd, **kwargs)
