"""Lemma CLI.

Top-level imports stay light: the console script is named ``lemma``, and importing
``bittensor`` at module load would register global argparse handlers that steal ``--help``.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click

from lemma import __version__
from lemma.cli.style import colors_enabled, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import get_problem_source, resolve_problem


@click.group(invoke_without_command=True, context_settings={"max_content_width": 100})
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Lemma subnet — Lean proofs + reasoning traces (Bittensor).

    \b
    Common commands:
      lemma-cli rehearsal  Live theorem → prover → Lean → judge (scoring preview)
      lemma-cli doctor     Config + keys + chain sanity
      lemma-cli        Friendly operator setup/help wrapper
      lemma --help     Full command list
    """
    if ctx.invoked_subcommand is None:
        click.echo(
            stylize("Lemma ", fg="cyan", bold=True)
            + stylize(__version__, dim=True)
            + stylize("  —  ", dim=True)
            + stylize("lemma-cli doctor", fg="green")
            + stylize(" checks · ", dim=True)
            + stylize("lemma-cli", fg="green")
            + stylize(" friendly setup · ", dim=True)
            + stylize("lemma COMMAND --help", fg="green")
            + stylize(" for one command\n", dim=True),
            nl=False,
        )
        click.echo(ctx.get_help(), color=colors_enabled())
        click.echo(stylize("Typical paths", fg="cyan", bold=True))
        click.echo(
            "  "
            + stylize("Miner", fg="yellow", bold=True)
            + stylize("       ", dim=True)
            + stylize("lemma-cli setup", fg="green")
            + stylize(" → ", dim=True)
            + stylize("btcli subnet register …", fg="green")
            + stylize(" → ", dim=True)
            + stylize("lemma miner dry-run", fg="green")
            + stylize(" → ", dim=True)
            + stylize("lemma miner start", fg="green"),
        )
        click.echo(
            "  "
            + stylize("Validator", fg="yellow", bold=True)
            + stylize("  ", dim=True)
            + stylize("bash scripts/prebuild_lean_image.sh", fg="green")
            + stylize(" → ", dim=True)
            + stylize("lemma validator-check", fg="green")
            + stylize(" → ", dim=True)
            + stylize("lemma validator start", fg="green"),
        )
        click.echo(
            "  "
            + stylize("Preview", fg="yellow", bold=True)
            + stylize("  ", dim=True)
            + stylize("lemma-cli rehearsal", fg="green")
            + stylize(" — prover + Lean + judge on the live theorem (costs APIs)", dim=True),
        )
        click.echo(stylize("  Docs: docs/getting-started.md · docs/miner.md · docs/validator.md\n", dim=True))
        return


@main.command("start")
def start_cmd() -> None:
    """Point guided onboarding users to lemma-cli."""
    click.echo(stylize("Guided setup moved to lemma-cli.", fg="cyan", bold=True))
    click.echo("Run `lemma-cli` or `lemma-cli start` for the friendly operator screen.")
    click.echo("Core commands still live here: `lemma miner start`, `lemma validator start`, `lemma verify`.")


@main.command(
    "doctor",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def doctor_cmd(args: tuple[str, ...]) -> None:
    """Point operator health checks to lemma-cli."""
    _echo_moved_to_lemma_cli(("doctor", *args), heading="Doctor moved to lemma-cli.")


@main.command(
    "docs",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def docs_cmd(args: tuple[str, ...]) -> None:
    """Point documentation helpers to lemma-cli."""
    _echo_moved_to_lemma_cli(("docs", *args), heading="Docs helper moved to lemma-cli.")


@main.command("meta")
@click.option(
    "--raw",
    is_flag=True,
    help="Compact key=value lines (original layout; best for scripts and copy-paste diffs).",
)
def meta_cmd(raw: bool) -> None:
    """Canonical fingerprints: generated templates + validator scoring profile."""
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
        click.echo(
            stylize(
                "Does not edit `.env`. To merge pins: ",
                dim=True,
            )
            + stylize("lemma-cli configure subnet-pins\n", fg="green", bold=True)
            + stylize("(publish hashes so every validator matches judge + templates)\n", dim=True),
            nl=False,
        )
        click.echo(f"lemma_version={__version__}")
        click.echo(f"problem_source={s.problem_source}")
        click.echo(f"generated_registry_sha256={reg_sha}")
        click.echo("generated_registry_json=" + json.dumps(reg, sort_keys=True))
        click.echo(f"judge_rubric_sha256={rub_sha}")
        click.echo(f"judge_profile_sha256={prof_sha}")
        click.echo("judge_profile_json=" + json.dumps(prof, sort_keys=True))
        rub_embed = str(prof.get("rubric_sha256", "")).strip().lower()
        rub_ok = rub_embed == rub_sha.strip().lower()
        click.echo(f"judge_profile_embedded_rubric_matches_code={'1' if rub_ok else '0'}")
        return

    click.echo(stylize("Subnet fingerprints", fg="cyan", bold=True))
    click.echo(
        stylize(
            "Why this exists: validators must agree on (1) which generated templates exist and "
            "(2) how answers are scored and accepted — otherwise weights are meaningless. "
            "Subnet operators publish these hashes so everyone runs the same stack.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(stylize("Update `.env` from this screen (validators)\n", fg="cyan"))
    click.echo(
        stylize("  This command only ", dim=True)
        + stylize("prints", fg="yellow")
        + stylize(" hashes. It does not edit files. To ", dim=True)
        + stylize("merge", fg="green")
        + stylize(" the current `judge_profile_sha256` and (if needed) generated-registry pin into ", dim=True)
        + stylize("`.env`", fg="yellow")
        + stylize(", run:\n", dim=True)
        + stylize("  lemma-cli configure subnet-pins\n", fg="green", bold=True)
        + stylize(
            "\n  That snapshots **today’s** `lemma meta` for your active env (match OPENAI_MODEL, Chutes URL, "
            "JUDGE_PROVIDER, etc. to the subnet first — then re-run if you change them).\n"
            "  Manual option: copy from ",
            dim=True,
        )
        + stylize("lemma meta --raw", fg="green")
        + stylize(" into `JUDGE_PROFILE_SHA256_EXPECTED` / `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`.\n", dim=True),
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
            " — fingerprint of your active validator scoring profile (no API keys): judge stack, rubric, "
            "problem cadence, verification timeouts, scoring blend, dedup, reputation, and protocol hooks "
            "that affect accepted responses. Two validators only match if all pinned fields match.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "Why yours may differ from someone else’s: different OPENAI_MODEL, JUDGE_TEMPERATURE, "
            "OPENAI_BASE_URL text, scoring settings, problem cadence, verifier policy, or repo version. "
            "That’s expected until you align env + git "
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
            "  2. Align judge env with the operator (OPENAI_MODEL, OPENAI_BASE_URL, JUDGE_PROVIDER, temps, …).\n"
            "  3. Run ",
            dim=True,
        )
        + stylize("lemma-cli configure subnet-pins", fg="green", bold=True)
        + stylize(
            " to write ",
            dim=True,
        )
        + stylize("JUDGE_PROFILE_SHA256_EXPECTED", fg="yellow")
        + stylize(" (and for generated problems ", dim=True)
        + stylize("LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED", fg="yellow")
        + stylize(") into `.env` from **this** checkout + env.\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(
            "     Or copy manually from ",
            dim=True,
        )
        + stylize("lemma meta --raw", fg="green")
        + stylize(" if you prefer editing `.env` by hand.\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(
            "  4. Validators refuse to start until pins match live `lemma meta` "
            "(expected lines must equal the SHA256 blocks below).\n",
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
            "  → write this value into `.env`: ",
            dim=True,
        )
        + stylize("lemma-cli configure subnet-pins", fg="green")
        + stylize("   (or paste into ", dim=True)
        + stylize("JUDGE_PROFILE_SHA256_EXPECTED", fg="yellow")
        + stylize(" yourself)\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(
            "  (compare this JSON to another validator — identical ⇒ same judge_profile_sha256.)\n",
            dim=True,
        ),
        nl=False,
    )
    for line in json.dumps(prof, indent=2, sort_keys=True).splitlines():
        click.echo(stylize(line, dim=True))

    rub_embed = str(prof.get("rubric_sha256", "")).strip().lower()
    rub_ok = rub_embed == rub_sha.strip().lower()
    click.echo(stylize("\nRubric alignment (easy check)\n", fg="cyan"))
    if rub_ok:
        click.echo(
            stylize("  ", dim=True)
            + stylize("OK", fg="green", bold=True)
            + stylize(
                "  The `rubric_sha256` field inside the judge profile JSON matches the "
                "“Judge rubric (code fingerprint)” "
                f"line ({rub_sha[:12]}…).\n",
                dim=True,
            ),
            nl=False,
        )
        click.echo(
            stylize(
                "  You do not need the two top-level hashes (rubric-only vs full profile) to be equal — "
                "the profile hash includes rubric + model + URL + sampling params.\n",
                dim=True,
            ),
            nl=False,
        )
    else:
        click.echo(
            stylize(
                "  MISMATCH — embedded rubric in profile JSON differs from `lemma.judge.fingerprint` "
                "(report this; it should not happen on a clean install).\n",
                fg="red",
                bold=True,
            ),
            err=True,
        )

    click.echo(
        stylize("\nTip: ", dim=True)
        + stylize("lemma-cli configure subnet-pins", fg="green", bold=True)
        + stylize(" merges pins into `.env`; ", dim=True)
        + stylize("lemma meta --raw", fg="green")
        + stylize(" is compact copy/paste + one-line JSON.\n", dim=True),
        nl=False,
    )


@main.command(
    "try-prover",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def try_prover_cmd(args: tuple[str, ...]) -> None:
    """Point local prover previews to lemma-cli."""
    _echo_moved_to_lemma_cli(("try-prover", *args), heading="try-prover moved to lemma-cli.")


@main.command(
    "rehearsal",
    context_settings={"ignore_unknown_options": True, "allow_extra_args": True},
    add_help_option=False,
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def rehearsal_cmd(args: tuple[str, ...]) -> None:
    """Point local scoring previews to lemma-cli."""
    _echo_moved_to_lemma_cli(("rehearsal", *args), heading="rehearsal moved to lemma-cli.")


@main.command("status")
def status_cmd() -> None:
    """Chain head + theorem seed (same rule as validators in ``run_epoch``)."""
    from lemma.common.block_deadline import forward_wait_at_chain_head
    from lemma.common.problem_seed import (
        blocks_until_challenge_may_change,
        effective_chain_head_for_problem_seed,
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
            "Problem seeds follow LEMMA_PROBLEM_SEED_MODE (see docs/faq.md).",
            err=True,
        )
        raise SystemExit(2) from e

    ps2, st2, deadline_b, forward_wait_s = forward_wait_at_chain_head(
        settings=settings,
        subtensor=subtensor,
        chain_head_block=block,
    )
    problem_seed, seed_tag = ps2, st2
    slack_b = int(settings.lemma_problem_seed_chain_head_slack_blocks or 0)
    seed_head = effective_chain_head_for_problem_seed(block, slack_b)
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
            "(see `lemma-cli glossary`).",
            dim=True,
        ),
    )
    click.echo(stylize("Chain & seed", fg="cyan"))
    click.echo(stylize("  chain_head       ", dim=True) + str(block))
    if slack_b > 0:
        click.echo(stylize("  problem_seed_chain_head ", dim=True) + str(seed_head))
        click.echo(stylize("  slack_blocks     ", dim=True) + str(slack_b))
    click.echo(stylize("  problem_seed     ", dim=True) + str(problem_seed))
    click.echo(stylize("  seed_tag         ", dim=True) + str(seed_tag))
    _bl, _ = blocks_until_challenge_may_change(
        chain_head_block=seed_head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        seed_tag=seed_tag,
        subtensor=subtensor,
    )
    _countdown = format_next_theorem_countdown(
        chain_head_block=seed_head,
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
        f"  {stylize('lemma-cli try-prover', fg='green')}  "
        + stylize("(bills prover API)", fg="yellow", bold=True),
    )
    click.echo(
        f"  {stylize('lemma-cli try-prover --verify', fg='green')}  "
        + stylize(
            "+ local Lean compile only (not validator scoring); add --host-lean to use host lake vs Docker",
            dim=True,
        ),
    )
    click.echo(f"  {stylize('lemma meta', fg='green')}  " + stylize("judge + template hashes", dim=True))


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
        + stylize("lemma miner observability", fg="green")
        + stylize(" — what you can see in this terminal · ", dim=True)
        + stylize("lemma-cli", fg="green")
        + stylize(" — friendly operator screen.\n", dim=True),
        nl=False,
    )


def _miner_emit_observability_panel() -> None:
    """Operator-facing: logs vs judge scores (synapse has no return grade)."""
    s = LemmaSettings()
    setup_logging(s.log_level)
    click.echo(stylize("\nMiner — observability (CLI)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "Validators score your response after the HTTP reply — the axon does not receive a judge grade "
            "back on the wire. You can still see your own outputs in logs and aggregate incentives on-chain.\n",
            dim=True,
        ),
    )
    click.echo(stylize("On this machine (stdout / logs)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        "  "
        + stylize("LEMMA_MINER_FORWARD_TIMELINE=1", fg="yellow")
        + stylize(
            " — three INFO lines per forward: RECEIVE (deadline vs head), SOLVED, OUTCOME "
            "(best view in this terminal).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LEMMA_MINER_LOG_FORWARDS=1", fg="yellow")
        + stylize(
            " — log INFO excerpts of reasoning + proof_script each forward (set in `.env` before ",
            dim=True,
        )
        + stylize("lemma miner start", fg="green")
        + stylize(").\n", dim=True),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LEMMA_MINER_FORWARD_SUMMARY=1", fg="yellow")
        + stylize(
            " — one line per forward (default on unless you disable it).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LEMMA_MINER_LOCAL_VERIFY=1", fg="yellow")
        + stylize(
            " — run Lean verify locally after each forward "
            "(same idea as validators’ kernel check; not the LLM judge).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        "  "
        + stylize("LOG_LEVEL=DEBUG", fg="yellow")
        + stylize(" — more verbose prover logging when debugging.\n", dim=True),
        nl=False,
    )
    click.echo(stylize("On-chain (aggregate, not one theorem’s judge score)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        "  "
        + stylize(
            f"btcli subnet show --netuid {s.netuid} --network {s.subtensor_network}",
            fg="green",
        )
        + stylize(
            " — incentive / stake / trust from the metagraph (updates as validators set weights).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "If you thought you saw a “judge score” in docs or logs: that is usually the validator pipeline "
            "(Lean → judge rubric → weights), described in docs/faq.md — "
            "not a score returned to the miner over HTTP.\n",
            dim=True,
        ),
    )
    click.echo(stylize("On the validator machine (not your miner)\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "  INFO lines like ",
            dim=True,
        )
        + stylize("lemma_epoch_summary … scored=N …", fg="yellow")
        + stylize(
            " count how many miners got a judge rubric that round. ",
            dim=True,
        )
        + stylize("lemma validator", fg="green")
        + stylize(
            " dry-runs may print weight snippets. With ",
            dim=True,
        )
        + stylize("LEMMA_TRAINING_EXPORT_JSONL", fg="yellow")
        + stylize(
            ", validators can append per-UID rubric rows to a JSONL file.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(stylize("Subnet round timing\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize(
            "Validators always wait for subnet epoch boundaries before each scoring round — same cadence for "
            "every operator; there is no timer-only mode in Lemma.\n",
            dim=True,
        ),
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
    help=(
        "Miner axon — receive validator forwards and run the prover LLM. "
        "Typical path: lemma-cli setup → btcli subnet register → lemma miner dry-run → lemma miner start."
    ),
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
    max_forwards_per_day: int | None,
) -> None:
    """Use explicit subcommands from scripts."""
    if ctx.invoked_subcommand is not None:
        return
    if max_forwards_per_day is not None:
        _miner_run_axon(max_forwards_per_day)
        return
    click.echo(ctx.get_help(), color=colors_enabled())
    click.echo("Use `lemma miner start` or `lemma miner dry-run`.")
    click.echo("For the friendly operator screen, use `lemma-cli`.")


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


@miner_group.command(
    "observability",
    help="Explain how to see forwards in logs vs on-chain incentives (judge scores are not returned to the axon).",
)
def miner_observability_cmd() -> None:
    _miner_emit_observability_panel()


MOVED_SETUP_CONTEXT = {
    "ignore_unknown_options": True,
    "allow_extra_args": True,
}
MOVED_CONFIGURE_COMMANDS = (
    "chain",
    "axon",
    "lean-image",
    "judge",
    "prover",
    "prover-model",
    "prover-retries",
    "subnet-pins",
)


def _echo_moved_to_lemma_cli(
    parts: tuple[str, ...],
    *,
    heading: str = "Interactive setup moved to lemma-cli.",
) -> None:
    command = " ".join(("lemma-cli", *parts))
    click.echo(stylize(heading, fg="cyan", bold=True))
    click.echo(f"Run `{command}`.")
    click.echo("Core commands still live here: `lemma miner start`, `lemma validator start`, `lemma verify`.")


@main.command("setup", context_settings=MOVED_SETUP_CONTEXT, add_help_option=False)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def setup_cmd(args: tuple[str, ...]) -> None:
    """Point first-time configuration users to lemma-cli."""
    _echo_moved_to_lemma_cli(("setup", *args))


@main.group("configure", invoke_without_command=True)
@click.pass_context
def configure_grp(ctx: click.Context) -> None:
    """Point interactive `.env` prompts to lemma-cli."""
    if ctx.invoked_subcommand is None:
        _echo_moved_to_lemma_cli(("configure",))
        click.echo("Topics: " + ", ".join(MOVED_CONFIGURE_COMMANDS))


def _register_moved_configure(command: str) -> None:
    @configure_grp.command(command, context_settings=MOVED_SETUP_CONTEXT, add_help_option=False)
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def moved_configure(args: tuple[str, ...], command: str = command) -> None:
        _echo_moved_to_lemma_cli(("configure", command, *args))


for _configure_command in MOVED_CONFIGURE_COMMANDS:
    _register_moved_configure(_configure_command)


@main.command("glossary")
def glossary_cmd() -> None:
    """Point short operator definitions to lemma-cli."""
    _echo_moved_to_lemma_cli(("glossary",), heading="Glossary moved to lemma-cli.")


def _validator_run_blocking(*, dry_run: bool) -> None:
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    ValidatorService(settings, dry_run=dry_run).run_blocking()


@main.group(
    "validator",
    invoke_without_command=True,
    help=(
        "Validator — query miners, Lean verify, LLM judge, optional set_weights. "
        "Local scoring preview (no metagraph): lemma-cli rehearsal. "
        "Judge-only on files: lemma judge --trace FILE. "
        "Typical path: bash scripts/prebuild_lean_image.sh → lemma validator-check → lemma validator start."
    ),
)
@click.pass_context
def validator_group(ctx: click.Context) -> None:
    """Use explicit subcommands from scripts."""
    if ctx.invoked_subcommand is not None:
        return
    click.echo(ctx.get_help(), color=colors_enabled())
    click.echo(
        "Use `lemma validator start`, `lemma validator dry-run`, `lemma validator config`, "
        "or `lemma validator-check`."
    )
    click.echo("For the friendly operator screen, use `lemma-cli`.")


@validator_group.command("start", help="Run scoring rounds until Ctrl+C.")
def validator_start_cmd() -> None:
    _validator_run_blocking(dry_run=False)


@validator_group.command(
    "dry-run",
    help=(
        "Full scoring epochs without set_weights (chain + miners + Lean). "
        "Judge defaults to FakeJudge; set LEMMA_DRY_RUN_REAL_JUDGE=1 for live judge HTTP. "
        "Judge-only smoke test: lemma judge --trace FILE."
    ),
)
def validator_group_dry_run_cmd() -> None:
    _validator_run_blocking(dry_run=True)


@validator_group.command(
    "judge-attest-serve",
    help=(
        "Tiny HTTP server: GET /lemma/judge_profile_sha256 (text/plain hash for peer quorum). "
        "Pair with LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS on other validators."
    ),
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8799, type=int, show_default=True)
def validator_judge_attest_serve_cmd(host: str, port: int) -> None:
    """Expose local judge_profile_sha256 for LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS probes."""
    from lemma.common.logging import setup_logging
    from lemma.validator.judge_profile_attest import serve_judge_profile_attest_forever

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    serve_judge_profile_attest_forever(host, port, settings)


def _echo_validator_dry_wallet_section(settings: LemmaSettings) -> None:
    """Explain which wallet names the validator process will load (incl. BT_WALLET_* fallback)."""
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


@validator_group.command(
    "config",
    help="Print validator env summary and exit (no scoring loop, no chain writes).",
)
def validator_config_cmd() -> None:
    """One-shot preview — unlike `lemma validator dry-run`, does not run the metronome loop."""
    settings = LemmaSettings()
    setup_logging(settings.log_level)
    click.echo("")
    click.echo(stylize("Validator — config summary (not `lemma validator dry-run`)", fg="cyan", bold=True))
    click.echo("")
    click.echo(stylize("What this is", fg="cyan", bold=True))
    click.echo("")
    click.echo(
        stylize(
            "  Prints a config summary from `.env` / the environment only — no miners queried, no Lean, "
            "no judge HTTP, no chain writes. Use it to eyeball wallets, netuid, judge URL, and timeouts before "
            "a real validator session.\n",
            dim=True,
        )
    )
    click.echo("")
    click.echo(stylize("See also", fg="cyan", bold=True))
    click.echo("")
    click.echo(
        stylize(
            "  • `lemma-cli rehearsal` — live theorem → prover → Lean (optional) → judge rubric (preview stacks).\n",
            dim=True,
        )
    )
    click.echo(
        stylize(
            "  • `lemma judge --trace FILE` — rubric only (you supply saved trace / proof files).\n",
            dim=True,
        )
    )
    click.echo(
        stylize(
            "  • `lemma validator dry-run` — full scoring epochs without set_weights; judge defaults to "
            "FakeJudge (set LEMMA_DRY_RUN_REAL_JUDGE=1 for live judge HTTP).\n",
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
    click.echo(
        stylize(
            "  Validator cadence: subnet epoch boundaries only (no env toggle — mandatory for all operators).",
            dim=True,
        ),
    )
    click.echo(f"  JUDGE_PROVIDER={settings.judge_provider}")
    click.echo(f"  OPENAI_BASE_URL={settings.openai_base_url}")
    click.echo(f"  OPENAI_MODEL={settings.openai_model}")
    jk = settings.judge_openai_api_key_resolved()
    if jk:
        src = (
            "JUDGE_OPENAI_API_KEY"
            if (settings.judge_openai_api_key or "").strip()
            else "OPENAI_API_KEY (legacy fallback)"
        )
        click.echo(stylize(f"  Judge OpenAI key: present (from {src})", dim=True))
    else:
        click.echo(stylize("  Judge OpenAI key: (missing — FakeJudge)", dim=True))
    prov_base = (settings.prover_openai_base_url or "").strip()
    if prov_base:
        click.echo(f"  PROVER_OPENAI_BASE_URL={settings.prover_openai_base_url_resolved()}")
    else:
        click.echo(
            stylize(
                "  PROVER_OPENAI_BASE_URL=(unset — miner prover uses OPENAI_BASE_URL above)",
                dim=True,
            ),
        )
    if settings.prover_openai_api_key and str(settings.prover_openai_api_key).strip():
        click.echo(
            stylize(
                "  PROVER_OPENAI_API_KEY=(set — miner prover uses this instead of OPENAI_API_KEY)",
                dim=True,
            ),
        )
    click.echo(
        stylize(
            "  Subnet judge default on Chutes: OPENAI_BASE_URL=https://llm.chutes.ai/v1",
            dim=True,
        ),
    )
    click.echo(
        f"  LEMMA_LEAN_VERIFY_MAX_CONCURRENT={settings.lemma_lean_verify_max_concurrent}  "
        f"LEMMA_JUDGE_MAX_CONCURRENT={settings.lemma_judge_max_concurrent}  "
        "(cap parallel Lean + judge calls per epoch)",
    )
    if settings.lean_verify_workspace_cache_dir is not None:
        click.echo(f"  LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR={settings.lean_verify_workspace_cache_dir}")
    else:
        click.echo(
            stylize(
                "  LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=(unset — no cross-verify .lake reuse on disk)",
                dim=True,
            ),
        )
    jto = settings.judge_llm_http_timeout_s
    click.echo(
        f"  LEMMA_JUDGE_LLM_RETRY_ATTEMPTS={settings.judge_llm_retry_attempts}  "
        f"LEMMA_JUDGE_HTTP_TIMEOUT_S={jto if jto is not None else '(unset — uses LEMMA_LLM_HTTP_TIMEOUT_S)'}",
    )
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
        + stylize("lemma-cli", fg="green")
        + stylize("                  Friendly operator screen", dim=True),
    )
    click.echo("")


@main.command(
    "validator-check",
    help="Pre-flight: chain, wallet UID, judge pins, Lean image (before `lemma validator start`).",
)
def validator_check_cmd() -> None:
    """RPC + registration + pins + Docker — see NOT READY / READY at end."""
    from lemma.cli.validator_check import run_validator_check

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    raise SystemExit(run_validator_check(settings))


@main.command("verify")
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
    help="Path to a Submission.lean file (not a directory). Example: ./my_proof.lean",
)
@click.option(
    "--host-lean",
    "host_lean",
    is_flag=True,
    default=False,
    help=(
        "Run lake on host (not Docker). Requires LEMMA_ALLOW_HOST_LEAN=1. "
        "Default is Docker (same as validators)."
    ),
)
def verify_cmd(problem_id: str, submission_path: Path, host_lean: bool) -> None:
    """Verify a Submission.lean file against a catalog problem."""
    from lemma.lean.verify_runner import run_lean_verify

    settings = LemmaSettings()
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException(
            "Host Lean is disabled. Use Docker (default) to match validators. "
            "Set LEMMA_ALLOW_HOST_LEAN=1 in `.env` for local debugging, then use --host-lean."
        )
    src = submission_path.read_text(encoding="utf-8")
    p = resolve_problem(settings, problem_id)
    use_docker = not host_lean and settings.lean_use_docker
    eff = settings.model_copy(update={"lean_use_docker": use_docker})
    vr = run_lean_verify(
        eff,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=p,
        proof_script=src,
    )
    click.echo(vr.model_dump_json(indent=2))
    sys.exit(0 if vr.passed else 1)


@main.command("lean-worker")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8787, type=int, show_default=True)
def lean_worker_cmd(host: str, port: int) -> None:
    """Run HTTP Lean verify worker (POST ``/verify``); pair with ``LEMMA_LEAN_VERIFY_REMOTE_URL`` on validators."""
    from lemma.common.logging import setup_logging
    from lemma.lean.worker_http import serve_forever

    setup_logging(LemmaSettings().log_level)
    serve_forever(host, port)


@main.command(
    "judge",
    context_settings={"max_content_width": 100},
    epilog=(
        "Mental model: like `lemma-cli try-prover` for miners (one-shot LLM check), but for the **validator judge** "
        "only — no chain sampling step, no Lean verify.\n"
        "\n"
        "For **prover + Lean + judge** on the live subnet theorem in one command, prefer `lemma-cli rehearsal`.\n"
        "For a full scoring rehearsal without writing weights, use `lemma validator dry-run` (Lean + pipeline; "
        "judge defaults to FakeJudge — set LEMMA_DRY_RUN_REAL_JUDGE=1 to use your real judge there).\n"
        "\n"
        "Each flag is a path to a UTF-8 text file. Theorem and proof default to “(none)” in the rubric if omitted.\n"
        "\n"
        "Examples:\n"
        "  lemma judge --trace reasoning.txt\n"
        "  lemma judge --trace trace.txt --theorem Challenge.lean --proof Submission.lean\n"
        "\n"
        "Configure like a validator: lemma-cli configure judge (or lemma-cli setup). With "
        "JUDGE_OPENAI_API_KEY (or legacy "
        "OPENAI_API_KEY), the real model runs; otherwise FakeJudge (no HTTP). LEMMA_FAKE_JUDGE=1 forces FakeJudge "
        "even with keys."
    ),
)
@click.option(
    "--theorem",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional. Path to theorem / Challenge.lean text sent to the rubric as “Formal theorem”.",
)
@click.option(
    "--trace",
    "trace_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Required. Path to the informal reasoning trace (miner-style narrative or numbered steps) "
        "the subnet judge scores."
    ),
)
@click.option(
    "--proof",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="Optional. Path to Submission.lean (or proof text) for the rubric’s proof section.",
)
def judge_cmd(
    theorem: Path | None,
    trace_path: Path | None,
    proof: Path | None,
) -> None:
    """One-shot judge rubric on local files (validator judge only — no Lean / metagraph / set_weights).

    For an end-to-end preview (prover → Lean → judge) on the live theorem, use ``lemma-cli rehearsal``.
    For the full scoring loop without on-chain weights, use ``lemma validator dry-run``.
    Pass ``--trace PATH`` to a UTF-8 file; it is not a flag-only switch.
    """
    if trace_path is None:
        raise click.UsageError(
            "Missing --trace PATH: PATH must be a file containing the informal reasoning trace "
            "(plain UTF-8 text), e.g. a copy of what your miner logs as reasoning.\n\n"
            "  lemma judge --trace ./my_trace.txt\n"
            "  lemma judge --help   # full options and examples"
        )

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    th = theorem.read_text(encoding="utf-8") if theorem else "(none)"
    tr = trace_path.read_text(encoding="utf-8")
    pr = proof.read_text(encoding="utf-8") if proof else "(none)"

    from lemma.cli.judge_hints import echo_judge_http_failure_hints
    from lemma.judge.one_shot import score_rubric

    try:
        score = asyncio.run(score_rubric(settings, th, tr, pr))
    except Exception as e:  # noqa: BLE001
        click.echo(stylize(f"Judge error: {e}", fg="red", bold=True), err=True)
        echo_judge_http_failure_hints(e, settings)
        raise SystemExit(1) from e
    click.echo(score.model_dump_json(indent=2))


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
    from lemma.common.problem_seed import effective_chain_head_for_problem_seed, resolve_problem_seed

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
        slack_b = int(settings.lemma_problem_seed_chain_head_slack_blocks or 0)
        seed_head = effective_chain_head_for_problem_seed(head, slack_b)
        seed, tag = resolve_problem_seed(
            chain_head_block=seed_head,
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
                f"chain_head={head}  problem_seed_chain_head={seed_head}  problem_seed={seed}  seed_tag={tag}\n",
                dim=True,
            ),
            nl=False,
        )
        echo_next_theorem_countdown(
            settings,
            chain_head_block=seed_head,
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
        slack_bb = int(settings.lemma_problem_seed_chain_head_slack_blocks or 0)
        seed_head_b = effective_chain_head_for_problem_seed(head, slack_bb)
        seed, tag = resolve_problem_seed(
            chain_head_block=seed_head_b,
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
                f"chain_head={head}  problem_seed_chain_head={seed_head_b}  problem_seed={seed}  seed_tag={tag}\n",
                dim=True,
            ),
            nl=False,
        )
        echo_next_theorem_countdown(
            settings,
            chain_head_block=seed_head_b,
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
