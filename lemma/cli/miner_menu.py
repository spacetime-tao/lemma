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
            "Validators reach your axon on AXON_PORT; each forward runs the prover, then logs the reply.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "Tip: set LEMMA_MINER_FORWARD_TIMELINE=1 in .env for RECEIVE → SOLVED → OUTCOME lines per forward; "
            "add LEMMA_MINER_LOCAL_VERIFY=1 for Lean PASS/FAIL in logs (Docker).\n",
            dim=True,
        ),
    )
    w = 14
    rows = (
        ("1", "start", "Run axon (bind port, wait for forwards)"),
        ("2", "dry-run", "Print axon / env only — no server"),
        ("3", "observability", "What logs show vs what chain shows"),
        ("4", "quit", "Exit"),
    )
    click.echo(stylize("  " + "—" * 56, dim=True))
    for num, name, desc in rows:
        click.echo(
            "  "
            + stylize(num, fg="yellow")
            + "  "
            + stylize(name.ljust(w), fg="green")
            + stylize(desc, dim=True),
        )
    click.echo(stylize("  " + "—" * 56, dim=True))
    click.echo(
        stylize("Non-interactive: ", dim=True)
        + stylize("lemma miner start", fg="yellow")
        + stylize("  ·  ", dim=True)
        + stylize("lemma miner dry-run", fg="yellow")
        + stylize("  ·  ", dim=True)
        + stylize("lemma miner observability", fg="yellow")
        + stylize("\n", dim=True),
        nl=False,
    )

    if not sys.stdin.isatty():
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
