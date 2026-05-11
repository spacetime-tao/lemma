from __future__ import annotations

import click

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging


def print_miner_observability() -> None:
    settings = LemmaSettings()
    setup_logging(settings.log_level)
    click.echo(stylize("\nMiner - observability\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "Validators verify and score your response after the HTTP reply; the axon does not receive a proof grade "
            "back on the wire. You can still see your own outputs in logs and aggregate incentives on-chain.\n",
            dim=True,
        ),
    )
    click.echo(stylize("On this machine (stdout / logs)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        "  "
        + stylize("LEMMA_MINER_FORWARD_TIMELINE=1", fg="yellow")
        + stylize(
            " - three INFO lines per forward: RECEIVE (deadline vs head), SOLVED, OUTCOME "
            "(best view in this terminal).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LEMMA_MINER_LOG_FORWARDS=1", fg="yellow")
        + stylize(" - log INFO excerpts of proof_script each forward.\n", dim=True),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LEMMA_MINER_FORWARD_SUMMARY=1", fg="yellow")
        + stylize(" - one line per forward (default on unless you disable it).\n", dim=True),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LEMMA_MINER_LOCAL_VERIFY=1", fg="yellow")
        + stylize(
            " - run Lean verify locally after each forward "
            "(same kernel check validators use before scoring verified proofs).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LOG_LEVEL=DEBUG", fg="yellow")
        + stylize(" - more verbose prover logging when debugging.\n", dim=True),
        nl=False,
    )
    click.echo(stylize("On-chain (aggregate, not one theorem's proof result)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        "  "
        + stylize(
            f"btcli subnet show --netuid {settings.netuid} --network {settings.subtensor_network}",
            fg="green",
        )
        + stylize(
            " - incentive / stake / trust from the metagraph (updates as validators set weights).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "Validators score proofs that verify for the theorem. "
            "No score is returned to the miner over HTTP.\n",
            dim=True,
        ),
    )
    click.echo(stylize("On the validator machine (not your miner)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize("  INFO lines like ", dim=True)
        + stylize("lemma_epoch_summary ... scored=N ...", fg="yellow")
        + stylize(" count how many miners had Lean-verified proofs that round. ", dim=True)
        + stylize("lemma validator", fg="green")
        + stylize(
            " dry-runs may print weight snippets. With ",
            dim=True,
        )
        + stylize("LEMMA_TRAINING_EXPORT_JSONL", fg="yellow")
        + stylize(", validators can append per-UID proof rows to a JSONL file.\n", dim=True),
        nl=False,
    )
    click.echo(stylize("Subnet round timing\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "Validators always wait for subnet epoch boundaries before each scoring round; there is no "
            "timer-only mode in Lemma.\n",
            dim=True,
        ),
    )
