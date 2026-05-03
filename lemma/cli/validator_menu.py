"""Interactive menu for ``lemma validator`` (no subcommand)."""

from __future__ import annotations

import sys

import click

from lemma.cli.style import stylize


def show_validator_menu(ctx: click.Context) -> None:
    """Print options and run a subcommand or sibling command (TTY)."""
    vg = ctx.command
    assert isinstance(vg, click.Group)
    root = ctx.find_root().command
    assert isinstance(root, click.Group)

    click.echo(stylize("\nLemma — validator\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "1–2 run the real scoring loop (miners, Lean, judge). 3–4 do not run scoring — they only print.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("1", fg="yellow")
        + "  "
        + stylize("start", fg="green")
        + "          Live loop until Ctrl+C — includes set_weights on chain\n"
        "  "
        + stylize("2", fg="yellow")
        + "  "
        + stylize("dry-run", fg="green")
        + "      Same live loop as 1, but never set_weights (still queries miners / Lean / judge)\n"
        "  "
        + stylize("3", fg="yellow")
        + "  "
        + stylize("config", fg="green")
        + "        Read `.env` and print a summary — no rounds, no miners (`lemma validator-dry`)\n"
        "  "
        + stylize("4", fg="yellow")
        + "  "
        + stylize("check", fg="green")
        + "        Pre-flight checklist — RPC, wallet UID, subnet pins, Docker → READY or NOT READY\n"
        "  "
        + stylize("5", fg="yellow")
        + "  "
        + stylize("quit", fg="green")
        + "         Exit\n",
        nl=False,
    )
    click.echo(
        stylize(
            "Shell: ",
            dim=True,
        )
        + stylize("lemma validator start", fg="yellow")
        + stylize("  ·  ", dim=True)
        + stylize("lemma validator dry-run", fg="yellow")
        + stylize("  ·  ", dim=True)
        + stylize("lemma validator-dry", fg="yellow")
        + stylize("  ·  ", dim=True)
        + stylize("lemma validator-check", fg="yellow")
        + stylize("\n", dim=True),
        nl=False,
    )

    if not sys.stdin.isatty():
        click.echo(
            stylize(
                "Non-interactive: use `lemma validator start`, `lemma validator dry-run`, `lemma validator-dry`, "
            "or `lemma validator-check`.",
                dim=True,
            ),
        )
        return

    choice = (click.prompt("Choose 1–5", default="1") or "1").strip().lower()
    if choice in ("5", "q", "quit"):
        click.echo(stylize("Bye.", dim=True))
        return
    if choice == "2":
        dr = vg.get_command(ctx, "dry-run")
        if dr:
            ctx.invoke(dr)
        return
    if choice == "3":
        prev = root.get_command(ctx, "validator-dry")
        if prev:
            ctx.invoke(prev)
        return
    if choice == "4":
        chk = root.get_command(ctx, "validator-check")
        if chk:
            ctx.invoke(chk)
        return
    # 1 — full start (operator can Ctrl+C; optional --dry-run via shell)
    st = vg.get_command(ctx, "start")
    if st:
        ctx.invoke(st, dry_run=False)
