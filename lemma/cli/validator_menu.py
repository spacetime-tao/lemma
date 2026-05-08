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
            "1–2 run the scoring loop (miners, Lean, rubric). 3–4 only print — no rounds.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "First time: ",
            dim=True,
        )
        + stylize("bash scripts/prebuild_lean_image.sh", fg="green")
        + stylize(" → ", dim=True)
        + stylize("lemma validator-check", fg="green")
        + stylize(" → ", dim=True)
        + stylize("lemma validator start", fg="green")
        + stylize("  ·  docs/validator.md\n", dim=True),
    )
    click.echo(
        stylize(
            "Preview: ",
            dim=True,
        )
        + stylize("lemma rehearsal", fg="green")
        + stylize(" = live theorem → prover → Lean → judge. ", dim=True)
        + stylize("lemma judge --trace FILE", fg="green")
        + stylize(" = judge-only. ", dim=True)
        + stylize("This menu’s dry-run", fg="yellow")
        + stylize(" runs the full pipeline; stub judge unless LEMMA_DRY_RUN_REAL_JUDGE=1.\n", dim=True),
    )
    w = 14
    rows = (
        ("1", "start", "Live loop until Ctrl+C — includes set_weights on chain"),
        ("2", "dry-run", "Same as 1 but no set_weights; judge=FakeJudge unless LEMMA_DRY_RUN_REAL_JUDGE=1"),
        ("3", "config", "Print `.env` summary — no rounds (`lemma validator-dry`)"),
        ("4", "check", "Pre-flight: RPC, wallet UID, Docker → READY or NOT READY"),
        ("5", "quit", "Exit"),
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
