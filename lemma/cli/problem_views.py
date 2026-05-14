"""Shared formatting for theorem identity and Challenge.lean output."""

from __future__ import annotations

from lemma.cli.style import stylize
from lemma.problems.base import Problem


def echo_problem_card(
    p: Problem,
    *,
    heading: str = "This theorem",
    show_lean_goal: bool = True,
) -> None:
    """Human-oriented summary for the locked theorem target."""
    import click

    click.echo(stylize(heading, fg="cyan", bold=True))
    click.echo(stylize("  id           ", dim=True) + stylize(p.id, fg="green"))
    click.echo(stylize("  name         ", dim=True) + stylize(p.theorem_name, fg="green"))
    ex = p.extra or {}
    topic_raw = ""
    if isinstance(ex, dict):
        topic_raw = str(ex.get("topic") or "").strip()
    if topic_raw:
        parts = [seg.replace("_", " ") for seg in topic_raw.split(".")]
        human = f"{parts[-2].title()} · {parts[-1]}" if len(parts) >= 2 else parts[0].title()
        click.echo(
            stylize("  area         ", dim=True)
            + stylize(human, fg="yellow", bold=True)
            + stylize(f"  ({topic_raw})", dim=True),
        )
    label = str(ex.get("difficulty") or "unlabeled") if isinstance(ex, dict) else "unlabeled"
    click.echo(
        stylize("  difficulty   ", dim=True)
        + stylize(label, fg="yellow", bold=True)
        + stylize("  (informational only)", dim=True),
    )
    if show_lean_goal:
        te = p.type_expr
        if len(te) > 140:
            te = te[:140] + " ..."
        click.echo(
            stylize("  Lean goal    ", dim=True)
            + te
            + stylize("  <- formal statement in Lean", dim=True),
        )


def echo_challenge_separator() -> None:
    import click

    click.echo("")
    click.echo(stylize("Challenge.lean (what validators send)", fg="cyan", bold=True))
    click.echo("")
