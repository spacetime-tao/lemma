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
        + "           Run the miner server (bind port, wait for forwards)\n"
        "  "
        + stylize("2", fg="yellow")
        + "  "
        + stylize("dry-run", fg="green")
        + "        Print axon / env summary only — no server\n"
        "  "
        + stylize("3", fg="yellow")
        + "  "
        + stylize("observability", fg="green")
        + "  What you can see in this terminal (logs vs chain)\n"
        "  "
        + stylize("4", fg="yellow")
        + "  "
        + stylize("quit", fg="green")
        + "             Exit\n",
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
        + stylize("  ·  ", dim=True)
        + stylize("lemma miner observability", fg="yellow")
        + stylize("\n", dim=True),
        nl=False,
    )

    if not sys.stdin.isatty():
        click.echo(
            stylize(
                "Non-interactive: `lemma miner start` · `lemma miner dry-run` · `lemma miner observability`.",
                dim=True,
            ),
        )
        return

    choice = (click.prompt("Choose 1–4", default="1") or "1").strip().lower()
    if choice in ("4", "q", "quit"):
        click.echo(stylize("Bye.", dim=True))
        return
    if choice == "2":
        dr = miner_g.get_command(ctx, "dry-run")
        if dr:
            ctx.invoke(dr)
        return
    if choice == "3":
        ob = miner_g.get_command(ctx, "observability")
        if ob:
            ctx.invoke(ob)
        return
    # default start
    st = miner_g.get_command(ctx, "start")
    if st:
        ctx.invoke(st, max_forwards_per_day=None)
