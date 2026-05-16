"""Validator config summary for operators."""

from __future__ import annotations

import click

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging


def _echo_validator_wallet_section(settings: LemmaSettings) -> None:
    cold_res, hot_res = settings.validator_wallet_names()
    oc = (settings.validator_wallet_cold or "").strip()
    oh = (settings.validator_wallet_hot or "").strip()
    click.echo(stylize("Signing keys (for `lemma validator start`)", fg="cyan", bold=True))
    click.echo("")
    click.echo(f"  cold  {cold_res!r}")
    click.echo(f"  hot   {hot_res!r}")
    click.echo("")
    if not oc and not oh:
        click.echo(
            stylize(
                "  BT_VALIDATOR_WALLET_COLD / BT_VALIDATOR_WALLET_HOT are not set - Lemma uses the same names "
                "as your miner (BT_WALLET_COLD / BT_WALLET_HOT).",
                dim=True,
            )
        )
        click.echo(
            stylize(
                "  Set BT_VALIDATOR_WALLET_* in `.env` if the validator should sign with different keys.\n",
                dim=True,
            )
        )
    else:
        click.echo(
            stylize(
                "  Each slot uses BT_VALIDATOR_WALLET_* when set; otherwise it falls back to "
                "BT_WALLET_* for that slot.\n",
                dim=True,
            )
        )


def print_validator_config() -> None:
    """Print validator env summary without scoring, Lean, or chain writes."""
    settings = LemmaSettings()
    setup_logging(settings.log_level)
    click.echo("")
    click.echo(stylize("Validator - config summary (not `lemma validator dry-run`)", fg="cyan", bold=True))
    click.echo("")
    click.echo(stylize("What this is", fg="cyan", bold=True))
    click.echo("")
    click.echo(
        stylize(
            "  Prints a config summary from `.env` / the environment only - no miners queried, no Lean, "
            "no chain writes. Use it to eyeball wallets, netuid, Lean policy, and timeouts before "
            "a real validator session.\n",
            dim=True,
        )
    )
    click.echo(stylize("See also", fg="cyan", bold=True))
    click.echo("")
    click.echo(stylize("  * `lemma proof preview` - live theorem -> prover -> Lean.\n", dim=True))
    click.echo(
        stylize(
            "  * `lemma validator dry-run` - proof-verification epochs without set_weights.\n",
            dim=True,
        )
    )
    _echo_validator_wallet_section(settings)
    click.echo(stylize("Other settings", fg="cyan", bold=True))
    click.echo("")
    click.echo(f"  netuid={settings.netuid}")
    click.echo(f"  problem_source={settings.problem_source}")
    click.echo(f"  LEAN_SANDBOX_IMAGE={settings.lean_sandbox_image}")
    click.echo(f"  LEAN_VERIFY_TIMEOUT_S={settings.lean_verify_timeout_s}")
    click.echo(
        f"  LEMMA_BLOCK_TIME_SEC_ESTIMATE={settings.block_time_sec_estimate}  "
        f"LEMMA_FORWARD_WAIT_MIN_S={settings.forward_wait_min_s}  "
        f"LEMMA_FORWARD_WAIT_MAX_S={settings.forward_wait_max_s}",
    )
    click.echo(
        stylize(
            "  Validator cadence: published problem-seed windows.",
            dim=True,
        ),
    )
    prov_base = (settings.prover_openai_base_url or "").strip()
    if prov_base:
        click.echo(f"  PROVER_OPENAI_BASE_URL={settings.prover_openai_base_url_resolved()}")
    else:
        click.echo(stylize("  PROVER_OPENAI_BASE_URL=(unset - miner prover uses OPENAI_BASE_URL above)", dim=True))
    if settings.prover_openai_api_key and str(settings.prover_openai_api_key).strip():
        click.echo(
            stylize(
                "  PROVER_OPENAI_API_KEY=(set - miner prover uses this instead of OPENAI_API_KEY)",
                dim=True,
            ),
        )
    click.echo(
        f"  LEMMA_LEAN_VERIFY_MAX_CONCURRENT={settings.lemma_lean_verify_max_concurrent}  "
        "(cap parallel Lean verify jobs per epoch)",
    )
    if settings.lean_verify_workspace_cache_dir is not None:
        click.echo(f"  LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR={settings.lean_verify_workspace_cache_dir}")
    else:
        click.echo(
            stylize(
                "  LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=(unset - no cross-verify .lake reuse on disk)",
                dim=True,
            ),
        )
    click.echo("")
    click.echo(stylize("Next steps", fg="cyan", bold=True))
    click.echo("")
    click.echo("  " + stylize("lemma validator check", fg="green") + stylize("  RPC, pins, Docker -> READY", dim=True))
    click.echo("  " + stylize("lemma validator start", fg="green") + stylize("       Full scoring loop", dim=True))
    click.echo(
        "  "
        + stylize("lemma validator dry-run", fg="green")
        + stylize("   Scoring loop without set_weights", dim=True),
    )
    click.echo("")
