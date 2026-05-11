"""Shared formatting for theorem identity and Challenge.lean previews."""

from __future__ import annotations

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings
from lemma.problems.base import Problem


def echo_problem_card(
    p: Problem,
    *,
    heading: str = "This theorem",
    show_lean_goal: bool = True,
    settings: LemmaSettings | None = None,
    synapse_timeout_s: float | None = None,
    show_timeout_help: bool = False,
) -> None:
    """Human-oriented summary: area, difficulty, builder, optional Lean goal + timeouts."""
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
    click.echo(
        stylize("  difficulty   ", dim=True)
        + stylize(p.split, fg="yellow", bold=True)
        + stylize("  (easy / medium / hard)", dim=True),
    )
    if isinstance(ex, dict) and ex.get("template_fn"):
        click.echo(stylize("  builder      ", dim=True) + stylize(str(ex["template_fn"]), fg="green"))
    if show_lean_goal:
        te = p.type_expr
        if len(te) > 140:
            te = te[:140] + " ..."
        click.echo(
            stylize("  Lean goal    ", dim=True)
            + te
            + stylize("  <- formal statement in Lean", dim=True),
        )
    if show_timeout_help and settings is not None and synapse_timeout_s is not None:
        llm_s = float(settings.llm_http_timeout_s)
        axon_s = float(synapse_timeout_s)
        click.echo("")
        click.echo(
            stylize(
                f"Mining: validator forward HTTP wait up to {axon_s:.0f}s "
                f"(blocks x block time; see LEMMA_FORWARD_WAIT_*). "
                f"Your AI call may run up to {llm_s:.0f}s (LEMMA_LLM_HTTP_TIMEOUT_S). "
                "Rule of thumb: LLM time fits inside validator wait.",
                dim=True,
            ),
        )


def echo_next_theorem_countdown(
    settings: LemmaSettings,
    *,
    chain_head_block: int,
    seed_tag: str,
    subtensor: object,
) -> None:
    """Print blocks / estimated wall-clock until the shared theorem may change."""
    import click

    from lemma.common.problem_seed import (
        blocks_until_challenge_may_change,
        format_next_theorem_countdown,
    )

    bl, _ = blocks_until_challenge_may_change(
        chain_head_block=chain_head_block,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        seed_tag=seed_tag,
        subtensor=subtensor,
    )
    countdown = format_next_theorem_countdown(
        chain_head_block=chain_head_block,
        blocks_until_theorem_changes=bl,
        seconds_per_block=float(settings.block_time_sec_estimate),
    )
    click.echo(stylize(f"  {countdown}", fg="yellow", bold=True))
    bt = float(settings.block_time_sec_estimate)
    click.echo(
        stylize(
            f"  ~{bt:.0f}s/block est. (LEMMA_BLOCK_TIME_SEC_ESTIMATE) - wall-clock is approximate.\n",
            dim=True,
        ),
        nl=False,
    )


def echo_challenge_separator() -> None:
    import click

    click.echo("")
    click.echo(stylize("Challenge.lean (what validators send)", fg="cyan", bold=True))
    click.echo("")
