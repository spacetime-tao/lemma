"""Lemma CLI.

Top-level imports stay light: the console script is named ``lemma``, and importing
``bittensor`` at module load would register global argparse handlers that steal ``--help``.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

import click

from lemma import __version__
from lemma.cli.style import finish_cli_output, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import get_problem_source, resolve_problem


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Lemma subnet — Lean proofs + reasoning traces.

    Run with no subcommand to open the START HERE menu (`lemma start`).
    Run `lemma N` (e.g. `lemma 7`) to jump straight to menu item N (same as `lemma start --quick-select N`).
    """
    if ctx.invoked_subcommand is None:
        from lemma.cli.start_screen import show_start_here

        show_start_here(ctx, group=main)


@main.command("start")
@click.option(
    "--quick-select",
    "quick_select",
    type=int,
    default=None,
    hidden=True,
    metavar="N",
)
@click.pass_context
def start_cmd(ctx: click.Context, quick_select: int | None) -> None:
    """STEP-BY-STEP onboarding (same as running `lemma` with no arguments)."""
    from lemma.cli.start_screen import run_quick_menu_step, show_start_here

    if quick_select is not None:
        run_quick_menu_step(ctx, group=main, step=quick_select)
        return
    show_start_here(ctx, group=main)


def _rewrite_lemma_argv_numeric_menu() -> None:
    """Turn ``lemma 7`` / ``lemma 7 --verify`` into ``lemma start --quick-select 7`` (+ extras in env)."""
    av = sys.argv
    if len(av) < 2:
        return
    if not av[1].isdigit():
        return
    os.environ["_LEMMA_QUICK_MENU_EXTRAS_JSON"] = json.dumps(av[2:])
    av[:] = [av[0], "start", "--quick-select", av[1]]


def _doctor_api_lines(s: LemmaSettings) -> tuple[list[str], bool]:
    """Lines about inference keys (never print secrets). Returns (lines, all_required_ok)."""
    lines: list[str] = []
    ok_all = True

    def _present(val: str | None) -> bool:
        return bool(val and str(val).strip())

    jp = (s.judge_provider or "openai").lower()
    pp = (s.prover_provider or "anthropic").lower()

    tasks: list[tuple[str, str]] = []
    if jp == "openai":
        tasks.append(("Judge", "openai"))
    elif jp == "anthropic":
        tasks.append(("Judge", "anthropic"))
    else:
        lines.append(f"INFO judge: JUDGE_PROVIDER={jp!r}")

    if pp == "openai":
        tasks.append(("Prover", "openai"))
    elif pp == "anthropic":
        tasks.append(("Prover", "anthropic"))
    else:
        lines.append(f"INFO prover: PROVER_PROVIDER={pp!r}")

    if tasks == [("Judge", "openai"), ("Prover", "openai")]:
        ok = _present(s.openai_api_key)
        ok_all = ok
        tag = "OK" if ok else "WARN"
        lines.append(
            f"{tag} Judge + prover (OpenAI-compatible): "
            + ("OPENAI_API_KEY present (hidden)" if ok else "OPENAI_API_KEY missing"),
        )
        return lines, ok_all

    for role, kind in tasks:
        if kind == "openai":
            ok = _present(s.openai_api_key)
            if not ok:
                ok_all = False
            tag = "OK" if ok else "WARN"
            lines.append(
                f"{tag} {role} (OpenAI-compatible): "
                + ("OPENAI_API_KEY present (hidden)" if ok else "OPENAI_API_KEY missing"),
            )
        else:
            ok = _present(s.anthropic_api_key)
            if not ok:
                ok_all = False
            tag = "OK" if ok else "WARN"
            lines.append(
                f"{tag} {role} (Anthropic): "
                + ("ANTHROPIC_API_KEY present (hidden)" if ok else "ANTHROPIC_API_KEY missing"),
            )

    return lines, ok_all


@main.command("doctor")
def doctor_cmd() -> None:
    """Quick checks: venv, config load, optional chain RPC."""
    ok = True
    keys_ok = True
    root = Path.cwd()
    click.echo(stylize("Lemma doctor\n", fg="cyan", bold=True), nl=False)
    if (root / ".venv").is_dir():
        click.echo("  OK  .venv (uv sync --extra dev)")
    else:
        click.echo("  MISSING .venv — run: uv sync --extra dev", err=True)
        ok = False
    try:
        s = LemmaSettings()
        click.echo(f"  OK  config  NETUID={s.netuid}  problem_source={s.problem_source}")
        key_lines, keys_ok = _doctor_api_lines(s)
        for ln in key_lines:
            click.echo(f"  {ln}")
        click.echo(
            stylize(
                "  (Inference lines above reflect active config — `.env` wins over shell exports unless "
                "LEMMA_PREFER_PROCESS_ENV=1.)",
                dim=True,
            ),
        )
        jp2 = (s.judge_provider or "openai").lower()
        pp2 = (s.prover_provider or "anthropic").lower()
        if jp2 == "openai":
            click.echo(
                stylize(
                    f"  Judge   OPENAI_MODEL={s.openai_model!r} @ {s.openai_base_url!r}",
                    dim=True,
                ),
            )
        elif jp2 == "anthropic":
            click.echo(stylize(f"  Judge   ANTHROPIC_MODEL={s.anthropic_model!r}", dim=True))
        if pp2 == "openai":
            pm = s.prover_model or s.openai_model
            click.echo(
                stylize(
                    f"  Prover  model={pm!r} @ {s.openai_base_url!r}  "
                    f"(miner prover — PROVER_MODEL is not used when scoring as a validator)",
                    dim=True,
                ),
            )
        elif pp2 == "anthropic":
            pm = s.prover_model or s.anthropic_model
            click.echo(
                stylize(
                    f"  Prover  model={pm!r}  "
                    f"(miner prover — PROVER_MODEL is not used when scoring as a validator)",
                    dim=True,
                ),
            )
        forward_wait: float | None = None
        try:
            from lemma.common.block_deadline import forward_wait_at_chain_head
            from lemma.common.subtensor import get_subtensor

            st = get_subtensor(s)
            head = int(st.get_current_block())
            _, _, _, forward_wait = forward_wait_at_chain_head(
                settings=s,
                subtensor=st,
                chain_head_block=head,
            )
        except Exception:
            forward_wait = None

        if forward_wait is not None:
            fw = float(forward_wait)
            hi = float(s.forward_wait_max_s)
            llm_t = float(s.llm_http_timeout_s)
            # Only WARN when the LLM budget cannot fit any round (exceeds clamp ceiling).
            # Near the end of an N-block window, forward HTTP wait is short — comparing LLM to that
            # head snapshot alone would WARN almost every day without indicating misconfiguration.
            if llm_t > hi + 0.01:
                click.echo(
                    stylize(
                        "  WARN  LEMMA_LLM_HTTP_TIMEOUT_S exceeds LEMMA_FORWARD_WAIT_MAX_S — "
                        "prover reads cannot finish inside any validator’s axon wait.",
                        fg="yellow",
                    ),
                    err=True,
                )
            elif llm_t > fw + 0.01:
                click.echo(
                    stylize(
                        f"  Note  Forward HTTP wait at this head is ~{fw:.0f}s (varies by block). "
                        f"LEMMA_LLM_HTTP_TIMEOUT_S={llm_t:.0f}s is fine earlier in the window; "
                        "lower it only if miners drop near rotations.",
                        dim=True,
                    ),
                )
            else:
                click.echo(
                    stylize(
                        f"  OK  timeouts  LLM HTTP wait ≤ forward HTTP wait (~{fw:.0f}s at current head)",
                        dim=True,
                    ),
                )
        elif s.llm_http_timeout_s > s.forward_wait_max_s + 0.01:
            click.echo(
                stylize(
                    "  WARN  LEMMA_LLM_HTTP_TIMEOUT_S > LEMMA_FORWARD_WAIT_MAX_S — "
                    "cannot fit any round’s forward wait.",
                    fg="yellow",
                ),
                err=True,
            )
        else:
            click.echo(
                stylize(
                    "  INFO  forward HTTP wait is block-derived — "
                    "connect chain RPC for a precise LLM vs forward check.",
                    dim=True,
                ),
            )
        if not (s.judge_profile_expected_sha256 or "").strip():
            click.echo(
                stylize(
                    "  Tip   optional pin: JUDGE_PROFILE_SHA256_EXPECTED from `lemma meta --raw` "
                    "(enforce with LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META=1)",
                    dim=True,
                ),
            )
    except Exception as e:  # noqa: BLE001
        click.echo(f"CONFIG ERROR: {e}", err=True)
        finish_cli_output()
        raise SystemExit(1) from e
    try:
        from lemma.common.subtensor import get_subtensor

        head = int(get_subtensor(s).get_current_block())
        click.echo(f"  OK  chain RPC  head_block={head}")
    except Exception as e:  # noqa: BLE001
        click.echo(f"  SKIP  chain RPC (offline OK): {e}")
    click.echo(
        stylize(
            "\n"
            "  Next:\n"
            "    • `lemma meta` — judge + template hashes (subnet alignment)\n"
            "    • `lemma validator-check` — before `lemma validator` (READY / NOT READY)\n"
            "    • `lemma start` · `lemma configure --help` · `lemma docs --pick`\n",
            dim=True,
        ),
        nl=False,
    )
    if not ok:
        finish_cli_output()
        raise SystemExit(1)
    if not keys_ok:
        click.echo(
            stylize(
                "\ndoctor: WARN — inference keys (validators need judge; miners need prover)",
                fg="yellow",
            ),
            err=True,
        )
    else:
        click.echo(stylize("\ndoctor: OK", fg="green"))
    finish_cli_output()


_DOCS_BY_SLUG: tuple[tuple[str, str], ...] = (
    ("getting-started", "docs/GETTING_STARTED.md"),
    ("faq", "docs/FAQ.md"),
    ("miner", "docs/MINER.md"),
    ("validator", "docs/VALIDATOR.md"),
    ("models", "docs/MODELS.md"),
    ("testing", "docs/TESTING.md"),
)
_DOC_REL_BY_SLUG: dict[str, str] = dict(_DOCS_BY_SLUG)


@main.command("docs")
@click.option(
    "--open",
    "open_slug",
    type=click.Choice([s for s, _ in _DOCS_BY_SLUG], case_sensitive=False),
    default=None,
    metavar="DOC",
    help=(
        "Open one doc in your default app (macOS open / Linux xdg-open / Windows). "
        "Example: lemma docs --open faq"
    ),
)
@click.option(
    "--pick",
    is_flag=True,
    help="Choose which doc to open (interactive menu).",
)
def docs_cmd(open_slug: str | None, pick: bool) -> None:
    """Print paths to main documentation files in this repository."""
    if pick and open_slug is not None:
        raise click.UsageError("Use either --pick or --open DOC, not both.")
    repo = Path(__file__).resolve().parents[2]
    click.echo(
        stylize("Docs", fg="cyan", bold=True)
        + stylize(
            " (repo paths; `lemma docs --open getting-started` or `lemma docs --pick`)\n",
            dim=True,
        ),
        nl=False,
    )
    for slug, rel in _DOCS_BY_SLUG:
        path = repo / rel
        exists = path.is_file()
        label = f"  [{slug}]  {path}" if exists else f"  [{slug}]  {rel} (not found)"
        click.echo(stylize(label, fg="green") if exists else stylize(label, fg="yellow"))

    chosen_slug = open_slug
    if pick:
        click.echo("")
        for i, (slug, _) in enumerate(_DOCS_BY_SLUG, start=1):
            click.echo(f"  {i}. {stylize(f'lemma docs --open {slug}', fg='green')}")
        n = click.prompt("Open which doc", type=click.IntRange(1, len(_DOCS_BY_SLUG)))
        chosen_slug = _DOCS_BY_SLUG[n - 1][0]

    if chosen_slug is None:
        return

    rel = _DOC_REL_BY_SLUG[chosen_slug]
    path = repo / rel
    from lemma.cli.open_help import open_paths_in_os

    opened = open_paths_in_os([path])
    if opened:
        click.echo(f"Opened: {opened}")
    else:
        click.echo(f"File not found: {path}", err=True)


@main.command("meta")
@click.option(
    "--raw",
    is_flag=True,
    help="Compact key=value lines (original layout; best for scripts and copy-paste diffs).",
)
def meta_cmd(raw: bool) -> None:
    """Canonical fingerprints: generated templates + judge rubric + your judge env (validator parity)."""
    import json

    from lemma.judge.fingerprint import rubric_sha256
    from lemma.judge.profile import judge_profile_dict, judge_profile_sha256
    from lemma.problems.generated import generated_registry_canonical_dict, generated_registry_sha256

    s = LemmaSettings()
    reg = generated_registry_canonical_dict()
    reg_sha = generated_registry_sha256()
    rub_sha = rubric_sha256()
    prof = judge_profile_dict(s)
    prof_sha = judge_profile_sha256(s)

    if raw:
        click.echo(stylize("Subnet fingerprints (`lemma meta --raw`)", fg="cyan", bold=True))
        click.echo(stylize("(publish hashes so every validator matches judge + templates)\n", dim=True), nl=False)
        click.echo(f"lemma_version={__version__}")
        click.echo(f"problem_source={s.problem_source}")
        click.echo(f"generated_registry_sha256={reg_sha}")
        click.echo("generated_registry_json=" + json.dumps(reg, sort_keys=True))
        click.echo(f"judge_rubric_sha256={rub_sha}")
        click.echo(f"judge_profile_sha256={prof_sha}")
        click.echo("judge_profile_json=" + json.dumps(prof, sort_keys=True))
        return

    click.echo(stylize("Subnet fingerprints", fg="cyan", bold=True))
    click.echo(
        stylize(
            "Why this exists: validators must agree on (1) which generated templates exist and "
            "(2) how the judge scores answers — otherwise weights are meaningless. "
            "Subnet operators publish these hashes so everyone runs the same stack.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(stylize("What you’re looking at\n", fg="cyan"))
    click.echo(
        stylize(
            "  • ",
            dim=True,
        )
        + stylize("generated_registry", fg="green")
        + stylize(
            " — catalog of theorem builders / splits for this repo version (changes when templates change).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize("  • ", dim=True)
        + stylize("judge_rubric", fg="green")
        + stylize(
            " — fingerprint of the judge rubric text in this repo. Same for everyone on the same lemma "
            "commit / release (unless you patch scoring locally).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize("  • ", dim=True)
        + stylize("judge_profile", fg="green")
        + stylize(
            " — fingerprint of your active judge configuration (no API keys): provider, model id, "
            "temperature, max_tokens, rubric ref, and for OpenAI-compatible judges the normalized "
            "OPENAI_BASE_URL. Two validators only match if all of those fields match — not just the model. "
            "The base URL is part of the hash (same logical endpoint must string-match after trimming).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "Why yours may differ from someone else’s: different OPENAI_MODEL, JUDGE_TEMPERATURE, "
            "OPENAI_BASE_URL text, or repo version (rubric). That’s expected until you align env + git "
            "with the subnet policy.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "Important: ",
            dim=True,
        )
        + stylize("judge_rubric_sha256", fg="yellow")
        + stylize(
            " and ",
            dim=True,
        )
        + stylize("judge_profile_sha256", fg="yellow")
        + stylize(
            " are meant to differ. The rubric hash is only the scoring instructions in code. "
            "The profile hash is the whole judge stack (model, URL, temps, …) and includes "
            '`rubric_sha256` as one field — so it cannot equal the rubric hash alone.\n',
            dim=True,
        ),
        nl=False,
    )
    click.echo(stylize("How to match other validators (same subnet policy)\n", fg="cyan"))
    click.echo(
        stylize(
            "  1. Use the same lemma release (git tag / commit) the subnet operator publishes.\n"
            "  2. Run ",
            dim=True,
        )
        + stylize("lemma meta --raw", fg="green")
        + stylize(
            " and copy into `.env`: ",
            dim=True,
        )
        + stylize("JUDGE_PROFILE_SHA256_EXPECTED", fg="yellow")
        + stylize(" = the printed ", dim=True)
        + stylize("judge_profile_sha256", fg="yellow")
        + stylize(
            " line; for generated templates also ",
            dim=True,
        )
        + stylize("LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED", fg="yellow")
        + stylize(".\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(
            "  3. Match judge env to that hash: same OPENAI_MODEL, OPENAI_BASE_URL text (after trimming), "
            "JUDGE_TEMPERATURE, JUDGE_MAX_TOKENS, JUDGE_PROVIDER (see judge_profile JSON below).\n"
            "  4. Optional: set LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META=1 so the process exits unless pins are set.\n",
            dim=True,
        ),
        nl=False,
    )

    click.echo(stylize("\nRelease\n", fg="cyan"))
    click.echo(f"  lemma_version     {__version__}")
    click.echo(f"  problem_source    {s.problem_source}")

    click.echo(stylize("\nGenerated problem registry\n", fg="cyan"))
    click.echo(stylize(f"  SHA256  {reg_sha}", dim=False))
    click.echo(stylize("  (canonical JSON below)\n", dim=True), nl=False)
    for line in json.dumps(reg, indent=2, sort_keys=True).splitlines():
        click.echo(stylize(line, dim=True))

    click.echo(stylize("\nJudge rubric (code fingerprint)\n", fg="cyan"))
    click.echo(f"  SHA256  {rub_sha}")

    click.echo(stylize("\nJudge profile (your environment)\n", fg="cyan"))
    click.echo(stylize(f"  SHA256  {prof_sha}", dim=False))
    click.echo(
        stylize(
            "  (compare this JSON to another validator — identical ⇒ same judge_profile_sha256.)\n",
            dim=True,
        ),
        nl=False,
    )
    for line in json.dumps(prof, indent=2, sort_keys=True).splitlines():
        click.echo(stylize(line, dim=True))

    click.echo(
        stylize("\nTip: ", dim=True)
        + stylize("lemma meta --raw", fg="green")
        + stylize(" repeats the old compact `key=value` + one-line JSON.\n", dim=True),
        nl=False,
    )


@main.command("try-prover")
@click.option(
    "--verify/--no-verify",
    "do_verify",
    default=False,
    help=(
        "After the LLM answers, run Lean verify (Docker/host). Without --verify you only see model output, "
        "not whether Submission.lean builds (slower when enabled)."
    ),
)
@click.option(
    "--block",
    type=int,
    default=None,
    help="Pretend chain head is this block when resolving the problem seed.",
)
@click.option(
    "--yes",
    "-y",
    "assume_yes",
    is_flag=True,
    default=False,
    help="Skip the confirmation prompt (for scripts; still bills your prover API).",
)
@click.option(
    "--retry-attempts",
    "retry_attempts",
    type=click.IntRange(1, 32),
    default=None,
    help="Override LEMMA_PROVER_LLM_RETRY_ATTEMPTS for this run only (default: from .env).",
)
def try_prover_cmd(
    do_verify: bool,
    block: int | None,
    assume_yes: bool,
    retry_attempts: int | None,
) -> None:
    """Manual one-shot prover run (like a dry exercise); the live axon miner solves each forward immediately."""
    from lemma.cli.try_prover import run_try_prover

    if not assume_yes:
        if not sys.stdin.isatty():
            raise click.ClickException(
                "Non-interactive terminal: `lemma try-prover` bills your prover API. "
                "Run again with --yes to confirm, or use a TTY.",
            )
        click.echo(
            stylize(
                "try-prover calls your prover API (Chutes, Anthropic, …) and may incur cost.",
                fg="yellow",
                bold=True,
            ),
        )
        if not click.confirm("Continue?", default=False):
            raise click.Abort()

    settings = LemmaSettings()
    run_try_prover(
        settings,
        verify=do_verify,
        block=block,
        prover_llm_retry_attempts=retry_attempts,
    )


@main.command("status")
def status_cmd() -> None:
    """Chain head + theorem seed (same rule as validators in ``run_epoch``)."""
    from lemma.common.block_deadline import forward_wait_at_chain_head
    from lemma.common.problem_seed import (
        blocks_until_challenge_may_change,
        format_next_theorem_countdown,
    )
    from lemma.common.subtensor import get_subtensor

    settings = LemmaSettings()
    src = get_problem_source(settings)
    try:
        subtensor = get_subtensor(settings)
        block = int(subtensor.get_current_block())
    except Exception as e:  # noqa: BLE001 — RPC/network misconfig
        click.echo(
            f"Could not read chain head ({e}). Check SUBTENSOR_* and RPC connectivity.",
            err=True,
        )
        click.echo(
            "Problem seeds follow LEMMA_PROBLEM_SEED_MODE (see docs/FAQ.md).",
            err=True,
        )
        raise SystemExit(2) from e

    ps2, st2, deadline_b, forward_wait_s = forward_wait_at_chain_head(
        settings=settings,
        subtensor=subtensor,
        chain_head_block=block,
    )
    problem_seed, seed_tag = ps2, st2
    p = src.sample(seed=problem_seed)
    from lemma.cli.problem_views import echo_problem_card

    click.echo(stylize("Lemma status", fg="cyan", bold=True))
    click.echo(
        stylize("Same problem draw as `run_epoch` for your NETUID and seed mode.\n", dim=True),
        nl=False,
    )
    click.echo(stylize("Config", fg="cyan"))
    click.echo(stylize("  NETUID                 ", dim=True) + str(settings.netuid))
    click.echo(stylize("  problem_source         ", dim=True) + str(settings.problem_source))
    click.echo(stylize("  LEMMA_PROBLEM_SEED_MODE", dim=True) + str(settings.problem_seed_mode))
    _mode = (settings.problem_seed_mode or "").strip().lower()
    if _mode == "quantize":
        click.echo(
            stylize("  LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS ", dim=True)
            + str(settings.problem_seed_quantize_blocks),
        )
    click.echo(
        stylize(
            "  → Same theorem as other validators: shared chain head + NETUID + seed mode "
            "(see `lemma glossary`).",
            dim=True,
        ),
    )
    click.echo(stylize("Chain & seed", fg="cyan"))
    click.echo(stylize("  chain_head       ", dim=True) + str(block))
    click.echo(stylize("  problem_seed     ", dim=True) + str(problem_seed))
    click.echo(stylize("  seed_tag         ", dim=True) + str(seed_tag))
    _bl, _ = blocks_until_challenge_may_change(
        chain_head_block=block,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        seed_tag=seed_tag,
        subtensor=subtensor,
    )
    _countdown = format_next_theorem_countdown(
        chain_head_block=block,
        blocks_until_theorem_changes=_bl,
        seconds_per_block=float(settings.block_time_sec_estimate),
    )
    click.echo(
        stylize("  " + _countdown, fg="yellow", bold=True),
    )
    click.echo(
        stylize(
            f"  Wall-clock is approximate: ~{float(settings.block_time_sec_estimate):.0f}s/block "
            "(LEMMA_BLOCK_TIME_SEC_ESTIMATE).",
            dim=True,
        ),
    )
    click.echo(
        stylize(
            f"  Axon reply budget  ~{forward_wait_s:.0f}s HTTP (from blocks left this window). "
            f"Finish before block {deadline_b}.",
            dim=True,
        ),
    )
    click.echo("")
    echo_problem_card(p, heading="Theorem snapshot", show_lean_goal=True)
    click.echo("")
    click.echo(stylize("Next commands", fg="cyan"))
    click.echo(
        f"  {stylize('lemma problems', fg='green')}  "
        + stylize("full Challenge.lean (current theorem)", dim=True),
    )
    click.echo(
        f"  {stylize('lemma try-prover', fg='green')}  "
        + stylize("(bills prover API)", fg="yellow", bold=True),
    )
    click.echo(
        f"  {stylize('lemma try-prover --verify', fg='green')}  "
        + stylize("+ compile Submission.lean locally (Lean build)", dim=True),
    )
    click.echo(f"  {stylize('lemma meta', fg='green')}  " + stylize("judge + template hashes", dim=True))


@main.command("leaderboard")
@click.option("--top", type=int, default=25, help="Rows to show (max 64).")
@click.option(
    "--sort",
    type=click.Choice(["stake", "incentive", "trust"]),
    default="stake",
    help="Metagraph sort key (not on-chain Lean proof rate).",
)
def leaderboard_cmd(top: int, sort: str) -> None:
    """Show subnet metagraph: stake / incentive (chain view, not per-theorem scores)."""
    from lemma.cli.leaderboard_cmd import run_leaderboard

    run_leaderboard(LemmaSettings(), top=top, sort=sort)


def _miner_apply_daily_cap(max_forwards_per_day: int | None) -> None:
    if max_forwards_per_day is not None:
        os.environ["MINER_MAX_FORWARDS_PER_DAY"] = str(max_forwards_per_day)


def _miner_emit_dry_run_summary() -> None:
    settings = LemmaSettings()
    setup_logging(settings.log_level)
    click.echo(stylize("\nMiner — dry-run (preview only)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "Nothing is listening yet: no axon process, no bind on AXON_PORT, validators cannot reach you. "
            "Below is what Lemma would use if you run ",
            dim=True,
        )
        + stylize("lemma miner start", fg="green")
        + stylize(".\n", dim=True),
        nl=False,
    )
    click.echo(stylize("── Would use ──\n", fg="cyan", bold=True), nl=False)
    click.echo(f"netuid={settings.netuid} axon_port={settings.axon_port}")
    ext = (settings.axon_external_ip or "").strip() or None
    if ext:
        click.echo(f"axon_external_ip={ext} (from AXON_EXTERNAL_IP)")
    elif settings.axon_discover_external_ip:
        from lemma.miner.public_ip import discover_public_ipv4

        discovered = discover_public_ipv4()
        if discovered:
            click.echo(
                f"axon_external_ip={discovered} "
                "(auto-discovered at startup if AXON_EXTERNAL_IP stays unset)"
            )
        else:
            click.echo(
                "axon_external_ip=<discovery failed — set AXON_EXTERNAL_IP to your public IPv4 "
                f"and ensure port {settings.axon_port} is reachable>"
            )
    else:
        click.echo("axon_external_ip=<unset; set AXON_EXTERNAL_IP or enable AXON_DISCOVER_EXTERNAL_IP>")
    click.echo("")
    click.echo(
        stylize(
            "When the real miner runs: LEMMA_MINER_FORWARD_SUMMARY=1 (default) logs one line per forward + "
            "session totals; LEMMA_MINER_LOG_FORWARDS=1 includes reasoning/proof excerpts; "
            "LEMMA_MINER_LOCAL_VERIFY=1 optional local Lean check.",
            dim=True,
        ),
    )
    click.echo(
        stylize(
            "\nNext: ",
            dim=True,
        )
        + stylize("lemma miner start", fg="green")
        + stylize(" — bind port and wait for validators · ", dim=True)
        + stylize("lemma miner", fg="green")
        + stylize(" — interactive menu.\n", dim=True),
        nl=False,
    )


def _miner_run_axon(max_forwards_per_day: int | None) -> None:
    from lemma.miner.service import MinerService

    _miner_apply_daily_cap(max_forwards_per_day)
    settings = LemmaSettings()
    setup_logging(settings.log_level)
    MinerService(settings).run()


@main.group(
    "miner",
    invoke_without_command=True,
    help="Miner axon — receive validator forwards and run the prover LLM.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Print axon settings only (no server). Same as `lemma miner dry-run`.",
)
@click.option(
    "--max-forwards-per-day",
    type=int,
    default=None,
    help=(
        "Cap prover forwards per UTC day (0=unlimited via env string); overrides MINER_MAX_FORWARDS_PER_DAY "
        "when starting the axon without `miner start`."
    ),
)
@click.pass_context
def miner_group(
    ctx: click.Context,
    dry_run: bool,
    max_forwards_per_day: int | None,
) -> None:
    """Interactive menu when run bare; use subcommands or flags from scripts."""
    if ctx.invoked_subcommand is not None:
        return
    if dry_run:
        _miner_emit_dry_run_summary()
        return
    if max_forwards_per_day is not None:
        _miner_run_axon(max_forwards_per_day)
        return
    from lemma.cli.miner_menu import show_miner_menu

    show_miner_menu(ctx)


@miner_group.command(
    "start",
    help="Listen on AXON_PORT for validator forwards (prover LLM). Press Ctrl+C to stop.",
)
@click.option(
    "--max-forwards-per-day",
    type=int,
    default=None,
    help="Cap successful forwards per UTC day (savings); 0=unlimited. Overrides MINER_MAX_FORWARDS_PER_DAY.",
)
def miner_start_cmd(max_forwards_per_day: int | None) -> None:
    _miner_run_axon(max_forwards_per_day)


@miner_group.command("dry-run", help="Print axon / env summary only — does not bind the port.")
def miner_group_dry_run_cmd() -> None:
    _miner_emit_dry_run_summary()


@main.command("miner-dry", help="Same as `lemma miner dry-run` (print axon settings, no server).")
def miner_dry_cmd() -> None:
    _miner_emit_dry_run_summary()


@main.command("setup")
@click.option(
    "--role",
    type=click.Choice(["miner", "validator", "both"]),
    default=None,
    help="If omitted, you will be prompted.",
)
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def setup_cmd(role: str | None, env_path: Path | None) -> None:
    """Interactive first-time configuration (chain, keys, axon / judge / Lean image). No manual .env editing."""
    from lemma.cli.env_wizard import run_setup

    path = env_path or Path.cwd() / ".env"
    chosen = role or click.prompt(
        "Role — miner (prover + axon), validator (judge + Lean image), or both",
        type=click.Choice(["miner", "validator", "both"]),
    )
    run_setup(path, chosen)


@main.group("configure")
def configure_grp() -> None:
    """Interactive prompts merged into `.env` (run from repo root)."""


@configure_grp.command("chain")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def configure_chain(env_path: Path | None) -> None:
    """Set NETUID, subtensor endpoint, and wallet names."""
    from lemma.cli.env_wizard import collect_chain_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect_chain_updates())


@configure_grp.command("axon")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def configure_axon(env_path: Path | None) -> None:
    """Set AXON_PORT for miners."""
    from lemma.cli.env_wizard import collect_axon_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect_axon_updates())


@configure_grp.command("lean-image")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def configure_lean_image(env_path: Path | None) -> None:
    """Write the subnet Lean sandbox image name (fixed tag; build with scripts/prebuild_lean_image.sh)."""
    from lemma.cli.env_wizard import collect_lean_image_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect_lean_image_updates())


@configure_grp.command("judge")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def configure_judge(env_path: Path | None) -> None:
    """Set validator judge (Chutes recommended, or Anthropic / custom OpenAI-compatible)."""
    from lemma.cli.env_wizard import collect_judge_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect_judge_updates())
    click.echo("Done. Run `lemma meta` after changing models or URLs.")


@configure_grp.command("prover")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def configure_prover(env_path: Path | None) -> None:
    """Set miner prover LLM (Chutes recommended, or Anthropic / custom OpenAI-compatible)."""
    from lemma.cli.env_wizard import collect_prover_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect_prover_updates())
    click.echo("Done. Run `lemma miner --dry-run` to confirm axon settings.")


@configure_grp.command("prover-model")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def configure_prover_model(env_path: Path | None) -> None:
    """Set PROVER_MODEL only (miner id; does not change judge OPENAI_MODEL / ANTHROPIC_MODEL)."""
    from lemma.cli.env_wizard import collect_prover_model_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect_prover_model_updates())
    click.echo("Done. Run `lemma doctor` or `lemma try-prover` to confirm.")


@configure_grp.command("prover-retries")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
def configure_prover_retries(env_path: Path | None) -> None:
    """Set LEMMA_PROVER_LLM_RETRY_ATTEMPTS (prover 429 / timeout retries per forward)."""
    from lemma.cli.env_wizard import collect_prover_retries_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect_prover_retries_updates())
    click.echo("Done. Miner and `lemma try-prover` pick this up on next run.")


@configure_grp.command("prover-system-append")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
@click.option(
    "--clear",
    is_flag=True,
    default=False,
    help="Remove append text (set LEMMA_PROVER_SYSTEM_APPEND empty).",
)
@click.option(
    "--file",
    "text_file",
    type=click.File(encoding="utf-8"),
    default=None,
    help="Read append text from a UTF-8 file (multiline policies).",
)
def configure_prover_system_append(
    env_path: Path | None,
    clear: bool,
    text_file: object | None,
) -> None:
    """Optional text appended after built-in PROVER_SYSTEM on every miner prover call (tone, audience, style).

    Does not replace JSON/proof rules in-repo. Use --file for long text; interactive mode offers $EDITOR.
    """
    from lemma.cli.env_wizard import collect_prover_system_append_updates
    from lemma.common.env_file import merge_dotenv

    path = env_path or Path.cwd() / ".env"
    click.echo(f"Merging into {path}")
    if clear and text_file is not None:
        raise click.UsageError("Use either --clear or --file, not both.")
    if clear:
        merge_dotenv(path, {"LEMMA_PROVER_SYSTEM_APPEND": ""})
        click.echo(stylize("Cleared LEMMA_PROVER_SYSTEM_APPEND.", fg="green"))
        click.echo("Done. Restart the miner / retry `lemma try-prover` to pick up.")
        return
    if text_file is not None:
        content = text_file.read()
        merge_dotenv(path, {"LEMMA_PROVER_SYSTEM_APPEND": content})
        click.echo(stylize(f"Wrote LEMMA_PROVER_SYSTEM_APPEND ({len(content)} characters).", fg="green"))
        click.echo("Done. Restart the miner / retry `lemma try-prover` to pick up.")
        return
    merge_dotenv(path, collect_prover_system_append_updates())
    click.echo(stylize("Wrote LEMMA_PROVER_SYSTEM_APPEND.", fg="green"))
    click.echo("Done. Restart the miner / retry `lemma try-prover` to pick up.")


@configure_grp.command("subnet-pins")
@click.option(
    "--env-file",
    "env_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Default: ./.env",
)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Skip confirmation (for scripts).",
)
def configure_subnet_pins(env_path: Path | None, yes: bool) -> None:
    """Write JUDGE_PROFILE_SHA256_EXPECTED (+ registry pin if generated) from **current** `lemma meta`.

    Align OPENAI_MODEL, OPENAI_BASE_URL, temps, etc. to subnet policy first — then this snapshots pins so
    validators can enforce match (with LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META=1).
    """
    from lemma.cli.env_wizard import collect_subnet_pin_updates
    from lemma.common.env_file import merge_dotenv

    settings = LemmaSettings()
    path = env_path or Path.cwd() / ".env"
    updates = collect_subnet_pin_updates(settings)
    click.echo("")
    click.echo(stylize("Configure — subnet pins", fg="cyan", bold=True))
    click.echo(
        stylize(
            "Merge checksums into `.env` so `lemma meta` and `lemma validator-check` agree "
            "(same numbers you see under `lemma meta`).",
            dim=True,
        )
    )
    click.echo("")
    click.echo(stylize("Will write", fg="cyan", bold=True))
    for k, v in updates.items():
        click.echo(stylize(f"  {k}=", fg="yellow", bold=True) + stylize(v, fg="green"))
    click.echo("")
    if not yes:
        click.confirm(
            stylize("Merge these lines into ", dim=True) + stylize(str(path), fg="cyan") + "?",
            abort=True,
        )
    click.echo(stylize(f"Merging into {path}", dim=True))
    merge_dotenv(path, updates)
    click.echo("")
    click.echo(stylize("Done — pins saved.", fg="green", bold=True))
    click.echo(
        stylize(
            "Your `.env` now expects the judge profile and generated-registry fingerprints from "
            "this checkout and env. Run ",
            dim=True,
        )
        + stylize("lemma validator-check", fg="green")
        + stylize(" next; the judge/registry lines should show OK.\n", dim=True),
        nl=False,
    )
    click.echo("")
    click.echo(stylize("Notes", fg="cyan", bold=True))
    click.echo(
        stylize(
            "• These values are snapshots only — they do not change how models are called.\n"
            "• If you set LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META=1, the validator exits when "
            "`lemma meta` drifts (e.g. you change OPENAI_MODEL or pull a release without "
            "running this command again).\n"
            "• `judge_rubric_sha256` and `judge_profile_sha256` are different hashes on purpose.\n",
            dim=True,
        )
    )
    finish_cli_output()


@main.command("glossary")
def glossary_cmd() -> None:
    """Short definitions for seeds, `lemma problems`, try-prover, dry-runs."""
    from lemma.cli.glossary import print_glossary

    print_glossary()


def _validator_run_blocking(*, dry_run: bool) -> None:
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    ValidatorService(settings, dry_run=dry_run).run_blocking()


@main.group(
    "validator",
    invoke_without_command=True,
    help="Validator — query miners, Lean verify, LLM judge, optional set_weights.",
)
@click.option(
    "--dry-run",
    "legacy_dry",
    is_flag=True,
    default=False,
    help="Run rounds without set_weights (legacy shortcut for `lemma validator dry-run`).",
)
@click.pass_context
def validator_group(ctx: click.Context, legacy_dry: bool) -> None:
    """Interactive menu when run bare."""
    if ctx.invoked_subcommand is not None:
        return
    if legacy_dry:
        _validator_run_blocking(dry_run=True)
        return
    from lemma.cli.validator_menu import show_validator_menu

    show_validator_menu(ctx)


@validator_group.command("start", help="Run scoring rounds until Ctrl+C.")
@click.option("--dry-run", is_flag=True, default=False, help="No on-chain set_weights this session.")
def validator_start_cmd(dry_run: bool) -> None:
    dr = dry_run or os.environ.get("LEMMA_DRY_RUN") == "1"
    _validator_run_blocking(dry_run=dr)


@validator_group.command("dry-run", help="Scoring rounds without set_weights.")
def validator_group_dry_run_cmd() -> None:
    _validator_run_blocking(dry_run=True)


def _echo_validator_dry_wallet_section(settings: LemmaSettings) -> None:
    """Explain which wallet names the validator process will load (incl. BT_WALLET_* fallback)."""
    cold_res, hot_res = settings.validator_wallet_names()
    oc = (settings.validator_wallet_cold or "").strip()
    oh = (settings.validator_wallet_hot or "").strip()
    click.echo(stylize("Signing keys (for `lemma validator`)", fg="cyan", bold=True))
    click.echo("")
    click.echo(f"  cold  {cold_res!r}")
    click.echo(f"  hot   {hot_res!r}")
    click.echo("")
    if not oc and not oh:
        click.echo(
            stylize(
                "  BT_VALIDATOR_WALLET_COLD / BT_VALIDATOR_WALLET_HOT are not set — Lemma uses the same names "
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


@main.command(
    "validator-dry",
    help="Print validator env summary and exit (no scoring loop, no chain writes).",
)
def validator_dry_cmd() -> None:
    """One-shot preview — unlike `lemma validator dry-run`, does not run the metronome loop."""
    settings = LemmaSettings()
    setup_logging(settings.log_level)
    click.echo("")
    click.echo(stylize("Validator — dry-run (preview only)", fg="cyan", bold=True))
    click.echo("")
    click.echo(stylize("What this is", fg="cyan", bold=True))
    click.echo("")
    click.echo(
        stylize(
            "  • Reads config only (your `.env` / environment). Nothing runs: no miners queried, no Lean, "
            "no judge HTTP, no chain writes.",
            dim=True,
        )
    )
    click.echo("")
    click.echo(
        stylize(
            "  • Use it to eyeball wallets, netuid, judge URL, and timeouts before a real validator session.",
            dim=True,
        )
    )
    click.echo("")
    _echo_validator_dry_wallet_section(settings)
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
    click.echo(f"  LEMMA_VALIDATOR_ROUND_INTERVAL_S={settings.validator_round_interval_s}")
    click.echo(f"  LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH={int(settings.validator_align_rounds_to_epoch)}")
    click.echo(f"  JUDGE_PROVIDER={settings.judge_provider}")
    click.echo(f"  OPENAI_BASE_URL={settings.openai_base_url}")
    click.echo(f"  OPENAI_MODEL={settings.openai_model}")
    click.echo("")
    click.echo(stylize("Next steps", fg="cyan", bold=True))
    click.echo("")
    click.echo(
        "  "
        + stylize("lemma validator-check", fg="green")
        + stylize("     RPC, registration, pins, Docker → READY / NOT READY", dim=True),
    )
    click.echo(
        "  "
        + stylize("lemma validator start", fg="green")
        + stylize("       Full scoring loop (Ctrl+C to stop)", dim=True),
    )
    click.echo(
        "  "
        + stylize("lemma validator dry-run", fg="green")
        + stylize("   Scoring loop without on-chain set_weights", dim=True),
    )
    click.echo(
        "  "
        + stylize("lemma validator", fg="green")
        + stylize("           Interactive menu", dim=True),
    )
    click.echo("")


@main.command(
    "validator-check",
    help="Pre-flight: chain, wallet UID, judge pins, Lean image (before `lemma validator`).",
)
def validator_check_cmd() -> None:
    """RPC + registration + pins + Docker — see NOT READY / READY at end."""
    from lemma.cli.validator_check import run_validator_check

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    raise SystemExit(run_validator_check(settings))


@main.command("verify")
@click.option("--problem", "problem_id", required=True)
@click.option("--submission", "submission_path", type=click.Path(exists=True), required=True)
def verify_cmd(problem_id: str, submission_path: str) -> None:
    """Verify a Submission.lean file against a catalog problem."""
    from lemma.lean.sandbox import LeanSandbox

    settings = LemmaSettings()
    src = Path(submission_path).read_text(encoding="utf-8")
    p = resolve_problem(settings, problem_id)
    sb = LeanSandbox(
        image=settings.lean_sandbox_image,
        cpu=settings.lean_sandbox_cpu,
        mem_mb=settings.lean_sandbox_mem_mb,
        timeout_s=settings.lean_verify_timeout_s,
        network_mode=settings.lean_sandbox_network,
    )
    vr = sb.verify(p, src)
    click.echo(vr.model_dump_json(indent=2))
    sys.exit(0 if vr.passed else 1)


@main.command("judge")
@click.option("--theorem", type=click.Path(exists=True))
@click.option("--trace", type=click.Path(exists=True), required=True)
@click.option("--proof", type=click.Path(exists=True))
def judge_cmd(theorem: str | None, trace: str, proof: str | None) -> None:
    """Smoke-test the LLM judge (requires API keys unless LEMMA_FAKE_JUDGE=1)."""
    from lemma.judge.anthropic_judge import AnthropicJudge
    from lemma.judge.base import Judge
    from lemma.judge.fake import FakeJudge
    from lemma.judge.openai_judge import OpenAIJudge

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    th = Path(theorem).read_text(encoding="utf-8") if theorem else "(none)"
    tr = Path(trace).read_text(encoding="utf-8")
    pr = Path(proof).read_text(encoding="utf-8") if proof else "(none)"

    async def _run() -> None:
        if os.environ.get("LEMMA_FAKE_JUDGE") == "1":
            j: Judge = FakeJudge()
        elif (settings.judge_provider or "").lower() == "openai" and settings.openai_api_key:
            j = OpenAIJudge(
                settings.openai_api_key,
                settings.openai_model,
                base_url=settings.openai_base_url,
                temperature=settings.judge_temperature,
                max_tokens=settings.judge_max_tokens,
            )
        elif settings.anthropic_api_key:
            j = AnthropicJudge(
                settings.anthropic_api_key,
                settings.anthropic_model,
                temperature=settings.judge_temperature,
                max_tokens=settings.judge_max_tokens,
            )
        else:
            j = FakeJudge()
        score = await j.score(th, tr, pr)
        click.echo(score.model_dump_json(indent=2))

    asyncio.run(_run())


@main.group("problems", invoke_without_command=True)
@click.pass_context
def problems_grp(ctx: click.Context) -> None:
    """Inspect catalog or print Challenge.lean (default: same as ``show --current``)."""
    if ctx.invoked_subcommand is None:
        show_cmd = ctx.command.get_command(ctx, "show")
        if show_cmd is None:
            raise click.ClickException("problems show command missing.")
        ctx.invoke(show_cmd, problem_id=None, current=True, block=None)


@problems_grp.command("list")
def problems_list() -> None:
    settings = LemmaSettings()
    src = get_problem_source(settings)
    rows = src.all_problems()
    if not rows:
        click.echo(
            "No rows to list (LEMMA_PROBLEM_SOURCE=generated uses infinite seed IDs gen/<block>). "
            "Set LEMMA_PROBLEM_SOURCE=frozen to enumerate minif2f_frozen.json."
        )
        return
    for p in rows:
        click.echo(f"{p.id}\t{p.split}\t{p.theorem_name}")


@problems_grp.command(
    "show",
    context_settings={"max_content_width": 100},
)
@click.argument("problem_id", required=False)
@click.option(
    "--current",
    "-c",
    is_flag=True,
    help="Use current chain head + LEMMA_PROBLEM_SEED_MODE (same as validators).",
)
@click.option(
    "--block",
    type=int,
    default=None,
    help="Treat N as chain head height; resolve seed like validators (see LEMMA_PROBLEM_SEED_MODE).",
)
def problems_show(problem_id: str | None, current: bool, block: int | None) -> None:
    """Print Challenge.lean source for one problem.

    Seed resolution matches ``run_epoch`` (``LEMMA_PROBLEM_SEED_MODE``): ``subnet_epoch`` uses subnet
    Tempo stride; ``quantize`` uses ``LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS``.

    With ``--current`` or ``--block``, also prints time / blocks until the next theorem (like ``lemma status``).

    With no arguments, defaults to ``--current`` (live chain head). Otherwise give exactly one of:
    PROBLEM_ID, ``--current`` / ``-c``, or ``--block N``.
    """
    from lemma.common.problem_seed import resolve_problem_seed

    settings = LemmaSettings()
    src = get_problem_source(settings)

    n_sel = sum([bool(problem_id and problem_id.strip()), current, block is not None])
    if n_sel == 0:
        current = True
    elif n_sel != 1:
        raise click.UsageError(
            "Give at most one of: PROBLEM_ID, --current (-c), or --block N (bare `lemma problems show` = current).",
        )

    from lemma.cli.problem_views import (
        echo_challenge_separator,
        echo_next_theorem_countdown,
        echo_problem_card,
    )

    if current:
        from lemma.common.subtensor import get_subtensor

        subtensor = get_subtensor(settings)
        head = int(subtensor.get_current_block())
        seed, tag = resolve_problem_seed(
            chain_head_block=head,
            netuid=settings.netuid,
            mode=settings.problem_seed_mode,
            quantize_blocks=settings.problem_seed_quantize_blocks,
            subtensor=subtensor,
        )
        p = src.sample(seed=seed)
        click.echo(stylize("lemma problems show --current", fg="cyan", bold=True))
        click.echo(
            stylize(
                "View: live chain — RPC head right now; same rotating theorem as validators.\n",
                fg="yellow",
            ),
            nl=False,
        )
        click.echo(
            stylize(
                f"chain_head={head}  problem_seed={seed}  seed_tag={tag}\n",
                dim=True,
            ),
            nl=False,
        )
        echo_next_theorem_countdown(
            settings,
            chain_head_block=head,
            seed_tag=tag,
            subtensor=subtensor,
        )
        echo_problem_card(p, heading="Theorem")
        echo_challenge_separator()
        click.echo(p.challenge_source())
        return

    if block is not None:
        from lemma.common.subtensor import get_subtensor

        subtensor = get_subtensor(settings)
        head = int(block)
        seed, tag = resolve_problem_seed(
            chain_head_block=head,
            netuid=settings.netuid,
            mode=settings.problem_seed_mode,
            quantize_blocks=settings.problem_seed_quantize_blocks,
            subtensor=subtensor,
        )
        p = src.sample(seed=seed)
        click.echo(stylize(f"lemma problems show --block {head}", fg="cyan", bold=True))
        click.echo(
            stylize(
                "View: simulated head — seed/countdown as if chain were at this height "
                "(your real RPC head may differ; use `lemma problems show --current` for live).\n",
                fg="yellow",
            ),
            nl=False,
        )
        click.echo(
            stylize(
                f"chain_head={head}  problem_seed={seed}  seed_tag={tag}\n",
                dim=True,
            ),
            nl=False,
        )
        echo_next_theorem_countdown(
            settings,
            chain_head_block=head,
            seed_tag=tag,
            subtensor=subtensor,
        )
        echo_problem_card(p, heading="Theorem")
        echo_challenge_separator()
        click.echo(p.challenge_source())
        return

    assert problem_id is not None  # guaranteed by n_sel with current/block exhausted
    p = resolve_problem(settings, problem_id.strip())
    click.echo(stylize(f"lemma problems show {problem_id.strip()}", fg="cyan", bold=True))
    click.echo(
        stylize(
            "View: fixed problem id — not the time-rotating challenge for the current block "
            "(unless this id happens to match today’s seed).\n",
            fg="yellow",
        ),
        nl=False,
    )
    click.echo("")
    echo_problem_card(p, heading="Theorem")
    echo_challenge_separator()
    click.echo(p.challenge_source())


@main.command("local-loop")
def local_loop_cmd() -> None:
    """Run one dry-run scoring epoch (no chain writes)."""
    from lemma.validator import epoch as ep

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    src = get_problem_source(settings)
    os.environ["LEMMA_FAKE_JUDGE"] = "1"
    os.environ["LEMMA_USE_DOCKER"] = "0"
    weights = asyncio.run(ep.run_epoch(settings, src, dry_run=True))
    click.echo(weights)


_rewrite_lemma_argv_numeric_menu()
