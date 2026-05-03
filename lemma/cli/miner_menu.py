"""Interactive menu for ``lemma miner`` (no subcommand)."""

from __future__ import annotations

import sys

import click

from lemma.cli.style import stylize


def show_miner_menu(ctx: click.Context) -> None:
    """Print options and run a subcommand (TTY), or print hint (non-TTY)."""
    miner_g = ctx.command
    assert isinstance(miner_g, click.Group)

    click.echo(stylize("\nLemma — miner\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "The axon listens on AXON_PORT; validators send theorem challenges and your prover returns JSON.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("1", fg="yellow")
        + "  "
        + stylize("start", fg="green")
        + "     Run the miner server (bind port, wait for forwards)\n"
        "  "
        + stylize("2", fg="yellow")
        + "  "
        + stylize("dry-run", fg="green")
        + "  Print axon / env summary only — no server\n"
        "  "
        + stylize("3", fg="yellow")
        + "  "
        + stylize("quit", fg="green")
        + "    Exit\n",
        nl=False,
    )
    click.echo(
        stylize(
            "Shell (non-interactive): ",
            dim=True,
        )
        + stylize("lemma miner start", fg="yellow")
        + stylize("  ·  ", dim=True)
        + stylize("lemma miner start --max-forwards-per-day 50", fg="yellow")
        + stylize("  ·  ", dim=True)
        + stylize("lemma miner dry-run", fg="yellow")
        + stylize("\n", dim=True),
        nl=False,
    )

    if not sys.stdin.isatty():
        click.echo(stylize("Non-interactive: use `lemma miner start` or `lemma miner dry-run`.", dim=True))
        return

    choice = (click.prompt("Choose 1–3", default="1") or "1").strip().lower()
    if choice in ("3", "q", "quit"):
        click.echo(stylize("Bye.", dim=True))
        return
    if choice == "2":
        dr = miner_g.get_command(ctx, "dry-run")
        if dr:
            ctx.invoke(dr)
        return
    # default start
    st = miner_g.get_command(ctx, "start")
    if st:
        ctx.invoke(st, max_forwards_per_day=None)
