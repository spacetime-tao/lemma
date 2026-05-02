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

   First-time path (copy-paste from your clone root):

     uv sync --extra dev
     ./scripts/lemma-run lemma setup

   (Or activate .venv, then `lemma setup` — same thing.)

 ----------------------------------------------------------------------
   Steps (details: docs/GETTING_STARTED.md)
 ----------------------------------------------------------------------
   1. Dependencies       uv sync --extra dev
   2. Configure env       lemma setup          (prompts; no manual .env)
   3. Wallets (manual)    btcli wallet new_coldkey / new_hotkey
   4. Register / fund     btcli subnet register … (per subnet)
   5. Miner               lemma miner
   6. Validator           bash scripts/prebuild_lean_image.sh
                          lemma validator

   Inspect chain / theorem (same sampling rule as validators):
                          lemma status
                          lemma problems show --current

 ----------------------------------------------------------------------
   Defaults (subnet tuning)
 ----------------------------------------------------------------------
   • ~5 min per challenge: DENDRITE_TIMEOUT_S / LEAN_VERIFY_TIMEOUT_S (300 s).
   • Validator rounds on a timer (LEMMA_VALIDATOR_ROUND_INTERVAL_S), not chain epochs,
     unless LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH=1.

 ======================================================================
"""
    )

    if ctx is None or group is None or not sys.stdin.isatty():
        click.echo("Tip: run `lemma start` anytime for this menu. Next: `lemma setup`")
        return

    choice = click.prompt(
        "Next step",
        type=click.Choice(
            ["setup", "status", "miner-dry", "validator-dry", "meta", "quit"],
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
