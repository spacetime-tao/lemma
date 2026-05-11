"""Lemma CLI.

Top-level imports stay light: the console script is named ``lemma``, and importing
``bittensor`` at module load would register global argparse handlers that steal ``--help``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import click

from lemma import __version__
from lemma.cli.style import colors_enabled, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import resolve_problem


@click.group(
    name="lemma",
    invoke_without_command=True,
    context_settings={"max_content_width": 100},
)
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Machine-checked formal proofs on Bittensor (Lean). See docs/litepaper.md."""
    if ctx.invoked_subcommand is None:
        _show_home(ctx)


def _home_help_commands(ctx: click.Context, *, include_usage: bool) -> None:
    """Print Usage (optional) + Commands + Options with the same palette as Quick start."""
    root = ctx.command
    if not isinstance(root, click.Group):
        raise click.ClickException("internal: expected a command group")
    name = root.name or "lemma"
    if include_usage:
        click.echo(stylize("Usage:", fg="cyan", bold=True) + f" {name} [OPTIONS] COMMAND [ARGS]...")
        click.echo("")
    click.echo(stylize("Commands:", fg="cyan", bold=True))
    for sub_name in sorted(root.commands):
        sub = root.commands[sub_name]
        h = sub.short_help or ""
        if not h and sub.help:
            h = sub.help.split("\n")[0].strip()
        h_one = (h or "—").strip().replace("\n", " ")
        if len(h_one) > 72:
            h_one = h_one[:69] + "..."
        pad = max(1, 18 - len(sub_name))
        click.echo(
            "  "
            + stylize(sub_name, fg="green", bold=True)
            + (" " * pad)
            + stylize(h_one, dim=True),
        )
    click.echo("")
    click.echo(stylize("Options:", fg="cyan", bold=True))
    click.echo(
        "  "
        + stylize("--version", fg="yellow", bold=True)
        + stylize("  Show the version and exit.", dim=True),
    )
    click.echo(
        "  "
        + stylize("--help", fg="yellow", bold=True)
        + stylize("     Show this message and exit.", dim=True),
    )


def _show_home(ctx: click.Context) -> None:
    click.echo(
        stylize("Lemma ", fg="cyan", bold=True)
        + stylize(__version__, dim=True)
        + stylize("  —  ", dim=True)
        + stylize("Machine-checked math proofs on Bittensor\n", fg="white"),
        nl=False,
    )
    name = ctx.command.name or "lemma"
    click.echo(stylize("Usage:", fg="cyan", bold=True) + f" {name} [OPTIONS] COMMAND [ARGS]...")
    click.echo("")
    click.echo(stylize("Quick start", fg="cyan", bold=True))
    click.echo(
        "  "
        + stylize("Setup", fg="yellow", bold=True)
        + stylize("      ", dim=True)
        + stylize("uv sync --extra btcli", fg="green")
        + stylize(" -> ", dim=True)
        + stylize("lemma setup", fg="green")
        + stylize(" -> ", dim=True)
        + stylize("lemma doctor", fg="green"),
    )
    click.echo(
        "  "
        + stylize("Miner", fg="yellow", bold=True)
        + stylize("      ", dim=True)
        + stylize("lemma preview", fg="green")
        + stylize(" -> ", dim=True)
        + stylize("lemma miner dry-run", fg="green")
        + stylize(" -> ", dim=True)
        + stylize("lemma miner start", fg="green"),
    )
    click.echo(
        "  "
        + stylize("Validator", fg="yellow", bold=True)
        + stylize("  ", dim=True)
        + stylize("bash scripts/prebuild_lean_image.sh", fg="green")
        + stylize(" -> ", dim=True)
        + stylize("lemma validator check", fg="green")
        + stylize(" -> ", dim=True)
        + stylize("lemma validator start", fg="green"),
    )
    click.echo(
        stylize("  Docs  docs/litepaper.md  ·  docs/faq.md  ·  docs/getting-started.md\n", dim=True),
        nl=False,
    )
    _home_help_commands(ctx, include_usage=False)


def _env_path(env_path: Path | None) -> Path:
    return env_path or Path.cwd() / ".env"


def _merge_env(env_path: Path | None, collect) -> None:
    from lemma.cli.env_file import merge_dotenv

    path = _env_path(env_path)
    click.echo(f"Merging into {path}")
    merge_dotenv(path, collect())


def _confirm_cost(command: str) -> None:
    if not sys.stdin.isatty():
        raise click.ClickException(
            f"Non-interactive terminal: `{command}` bills your prover API. "
            "Run again with --yes to confirm, or use a TTY.",
        )
    click.echo(stylize(f"{command} calls your prover API and may incur cost.", fg="yellow", bold=True))
    if not click.confirm("Continue?", default=False):
        raise click.Abort()


def _resolve_lean_backend(host_lean: bool, docker_verify: bool) -> bool | None:
    if host_lean and docker_verify:
        raise click.ClickException("Use only one of --host-lean and --docker-verify.")
    return False if host_lean else True if docker_verify else None


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
    """Interactive first-time configuration."""
    from lemma.cli.env_wizard import run_setup

    chosen = role or click.prompt(
        "Role — miner (prover + axon), validator (Lean image + pins), or both",
        type=click.Choice(["miner", "validator", "both"]),
    )
    run_setup(_env_path(env_path), chosen)


@main.command("doctor")
def doctor_cmd() -> None:
    """Check local environment, config, keys, and optional chain RPC."""
    from lemma.cli.doctor import run_doctor

    raise SystemExit(run_doctor())


@main.command("status")
def status_cmd() -> None:
    """Show chain head, theorem seed, and the current theorem preview."""
    from lemma.cli.problem_views import echo_problem_card
    from lemma.common.block_deadline import forward_wait_at_chain_head
    from lemma.common.problem_seed import (
        blocks_until_challenge_may_change,
        effective_chain_head_for_problem_seed,
        format_next_theorem_countdown,
    )
    from lemma.common.subtensor import get_subtensor
    from lemma.problems.factory import get_problem_source

    settings = LemmaSettings()
    src = get_problem_source(settings)
    try:
        subtensor = get_subtensor(settings)
        block = int(subtensor.get_current_block())
    except Exception as e:  # noqa: BLE001
        click.echo(f"Could not read chain head ({e}). Check SUBTENSOR_* and RPC connectivity.", err=True)
        click.echo("Problem seeds follow LEMMA_PROBLEM_SEED_MODE (see docs/technical-reference.md).", err=True)
        raise SystemExit(2) from e

    problem_seed, seed_tag, deadline_b, forward_wait_s = forward_wait_at_chain_head(
        settings=settings,
        subtensor=subtensor,
        chain_head_block=block,
    )
    slack_b = int(settings.lemma_problem_seed_chain_head_slack_blocks or 0)
    seed_head = effective_chain_head_for_problem_seed(block, slack_b)
    p = src.sample(seed=problem_seed)

    click.echo(stylize("Lemma status", fg="cyan", bold=True))
    click.echo(stylize("Same problem draw as validators for your NETUID and seed mode.\n", dim=True), nl=False)
    click.echo(stylize("Config", fg="cyan"))
    click.echo(stylize("  NETUID                 ", dim=True) + str(settings.netuid))
    click.echo(stylize("  problem_source         ", dim=True) + str(settings.problem_source))
    click.echo(stylize("  LEMMA_PROBLEM_SEED_MODE", dim=True) + str(settings.problem_seed_mode))
    if (settings.problem_seed_mode or "").strip().lower() == "quantize":
        click.echo(
            stylize("  LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS ", dim=True)
            + str(settings.problem_seed_quantize_blocks),
        )
    click.echo(stylize("Chain & seed", fg="cyan"))
    click.echo(stylize("  chain_head       ", dim=True) + str(block))
    if slack_b > 0:
        click.echo(stylize("  problem_seed_chain_head ", dim=True) + str(seed_head))
        click.echo(stylize("  slack_blocks     ", dim=True) + str(slack_b))
    click.echo(stylize("  problem_seed     ", dim=True) + str(problem_seed))
    click.echo(stylize("  seed_tag         ", dim=True) + str(seed_tag))
    blocks_left, _ = blocks_until_challenge_may_change(
        chain_head_block=seed_head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        seed_tag=seed_tag,
        subtensor=subtensor,
    )
    countdown = format_next_theorem_countdown(
        chain_head_block=seed_head,
        blocks_until_theorem_changes=blocks_left,
        seconds_per_block=float(settings.block_time_sec_estimate),
    )
    click.echo(stylize("  " + countdown, fg="yellow", bold=True))
    click.echo(
        stylize(
            f"  Axon reply budget  ~{forward_wait_s:.0f}s HTTP. Finish before block {deadline_b}.",
            dim=True,
        ),
    )
    click.echo("")
    echo_problem_card(p, heading="Theorem snapshot", show_lean_goal=True)
    click.echo("")
    click.echo(stylize("Next commands", fg="cyan"))
    click.echo(f"  {stylize('lemma problems', fg='green')}  " + stylize("full Challenge.lean", dim=True))
    click.echo(f"  {stylize('lemma preview', fg='green')}  " + stylize("(bills prover API)", fg="yellow", bold=True))
    click.echo(f"  {stylize('lemma meta', fg='green')}  " + stylize("validator profile + template hashes", dim=True))


@main.group("problems", invoke_without_command=True)
@click.pass_context
def problems_group(ctx: click.Context) -> None:
    """Inspect catalog or print Challenge.lean."""
    if ctx.invoked_subcommand is None:
        grp = ctx.command
        if not isinstance(grp, click.Group):
            raise click.ClickException("problems command group misconfigured.")
        show_cmd = grp.get_command(ctx, "show")
        if show_cmd is None:
            raise click.ClickException("problems show command missing.")
        ctx.invoke(show_cmd, problem_id=None, current=True, block=None)


@problems_group.command("list")
def problems_list_cmd() -> None:
    """List frozen catalog problems, when the active source is enumerable."""
    from lemma.problems.factory import get_problem_source

    settings = LemmaSettings()
    rows = get_problem_source(settings).all_problems()
    if not rows:
        click.echo(
            "No rows to list (LEMMA_PROBLEM_SOURCE=generated uses infinite seed IDs gen/<block>). "
            "Set LEMMA_PROBLEM_SOURCE=frozen to enumerate minif2f_frozen.json.",
        )
        return
    for p in rows:
        click.echo(f"{p.id}\t{p.split}\t{p.theorem_name}")


@problems_group.command("show", context_settings={"max_content_width": 100})
@click.argument("problem_id", required=False)
@click.option("--current", "-c", is_flag=True, help="Use current chain head + LEMMA_PROBLEM_SEED_MODE.")
@click.option("--block", type=int, default=None, help="Treat N as chain head height; resolve seed like validators.")
def problems_show_cmd(problem_id: str | None, current: bool, block: int | None) -> None:
    """Print Challenge.lean source for one problem."""
    from lemma.cli.problem_views import echo_challenge_separator, echo_next_theorem_countdown, echo_problem_card
    from lemma.common.problem_seed import effective_chain_head_for_problem_seed, resolve_problem_seed
    from lemma.common.subtensor import get_subtensor
    from lemma.problems.factory import get_problem_source

    settings = LemmaSettings()
    src = get_problem_source(settings)
    n_sel = sum([bool(problem_id and problem_id.strip()), current, block is not None])
    if n_sel == 0:
        current = True
    elif n_sel != 1:
        raise click.UsageError(
            "Give at most one of: PROBLEM_ID, --current (-c), or --block N "
            "(bare `lemma problems show` = current).",
        )

    if current or block is not None:
        subtensor = get_subtensor(settings)
        if current:
            head = int(subtensor.get_current_block())
        else:
            if block is None:
                raise click.UsageError("Expected --block N when --current is not set.")
            head = int(block)
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
        label = "lemma problems show --current" if current else f"lemma problems show --block {head}"
        click.echo(stylize(label, fg="cyan", bold=True))
        click.echo(stylize(f"chain_head={head}  problem_seed_chain_head={seed_head}  problem_seed={seed}\n", dim=True))
        echo_next_theorem_countdown(settings, chain_head_block=seed_head, seed_tag=tag, subtensor=subtensor)
        echo_problem_card(p, heading="Theorem")
        echo_challenge_separator()
        click.echo(p.challenge_source())
        return

    if problem_id is None:
        raise click.UsageError("problem_id is required unless using --current or --block.")
    p = resolve_problem(settings, problem_id.strip())
    click.echo(stylize(f"lemma problems show {problem_id.strip()}", fg="cyan", bold=True))
    click.echo("")
    echo_problem_card(p, heading="Theorem")
    echo_challenge_separator()
    click.echo(p.challenge_source())


@main.command("preview")
@click.option("--verify/--no-verify", "do_verify", default=True, help="After the prover answers, run Lean verify.")
@click.option("--block", type=int, default=None, help="Pretend chain head is this block.")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip the API-cost prompt.")
@click.option(
    "--retry-attempts",
    "retry_attempts",
    type=click.IntRange(1, 32),
    default=None,
    help="Override LEMMA_PROVER_LLM_RETRY_ATTEMPTS for this run only.",
)
@click.option("--host-lean", "host_lean", is_flag=True, help="Only with --verify: force host `lake`.")
@click.option("--docker-verify", "docker_verify", is_flag=True, help="Only with --verify: force Docker.")
def preview_cmd(
    do_verify: bool,
    block: int | None,
    assume_yes: bool,
    retry_attempts: int | None,
    host_lean: bool,
    docker_verify: bool,
) -> None:
    """Live theorem -> prover -> optional Lean proof preview."""
    from lemma.cli.preview import assert_preview_host_lean_allowed, run_preview

    if not assume_yes:
        _confirm_cost("lemma preview")
    settings = LemmaSettings()
    assert_preview_host_lean_allowed(settings, verify=do_verify, host_lean=host_lean)
    run_preview(
        settings,
        verify=do_verify,
        block=block,
        prover_llm_retry_attempts=retry_attempts,
        lean_use_docker=_resolve_lean_backend(host_lean, docker_verify),
    )


@main.group("configure")
def configure_group() -> None:
    """Interactive prompts merged into `.env`."""


@configure_group.command("chain")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def configure_chain_cmd(env_path: Path | None) -> None:
    """Set Bittensor testnet chain, endpoint, and wallet names."""
    from lemma.cli.env_wizard import collect_chain_updates

    _merge_env(env_path, collect_chain_updates)


@configure_group.command("axon")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def configure_axon_cmd(env_path: Path | None) -> None:
    """Set AXON_PORT for miners."""
    from lemma.cli.env_wizard import collect_axon_updates

    _merge_env(env_path, collect_axon_updates)


@configure_group.command("lean-image")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def configure_lean_image_cmd(env_path: Path | None) -> None:
    """Write the subnet Lean sandbox image name."""
    from lemma.cli.env_wizard import collect_lean_image_updates

    _merge_env(env_path, collect_lean_image_updates)


@configure_group.command("prover")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def configure_prover_cmd(env_path: Path | None) -> None:
    """Set miner prover LLM settings."""
    from lemma.cli.env_wizard import collect_prover_updates

    _merge_env(env_path, collect_prover_updates)
    click.echo("Done. Run `lemma miner dry-run` to confirm axon settings.")


@configure_group.command("prover-model")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def configure_prover_model_cmd(env_path: Path | None) -> None:
    """Set PROVER_MODEL only."""
    from lemma.cli.env_wizard import collect_prover_model_updates

    _merge_env(env_path, collect_prover_model_updates)
    click.echo("Done. Run `lemma doctor` or `lemma preview` to confirm.")


@configure_group.command("prover-retries")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def configure_prover_retries_cmd(env_path: Path | None) -> None:
    """Set prover retry attempts."""
    from lemma.cli.env_wizard import collect_prover_retries_updates

    _merge_env(env_path, collect_prover_retries_updates)
    click.echo("Done. Miner and `lemma preview` pick this up on next run.")


@configure_group.command("subnet-pins")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def configure_subnet_pins_cmd(env_path: Path | None, yes: bool) -> None:
    """Write expected subnet hash pins from the current Lemma checkout."""
    from lemma.cli.env_file import merge_dotenv
    from lemma.cli.env_wizard import collect_subnet_pin_updates

    path = _env_path(env_path)
    updates = collect_subnet_pin_updates(LemmaSettings())
    click.echo("")
    click.echo(stylize("Configure — subnet pins", fg="cyan", bold=True))
    click.echo("Will write")
    for key, value in updates.items():
        click.echo(stylize(f"  {key}=", fg="yellow", bold=True) + stylize(value, fg="green"))
    click.echo("")
    if not yes:
        click.confirm(f"Merge these lines into {path}?", abort=True)
    click.echo(stylize(f"Merging into {path}", dim=True))
    merge_dotenv(path, updates)
    click.echo(stylize("Done — pins saved.", fg="green", bold=True))


@main.command("meta")
@click.option(
    "--raw",
    is_flag=True,
    help="Compact key=value lines (best for scripts and copy-paste diffs).",
)
def meta_cmd(raw: bool) -> None:
    """Canonical fingerprints: generated templates + validator scoring profile."""
    import json

    from lemma.judge.profile import judge_profile_dict, judge_profile_sha256
    from lemma.problems.generated import generated_registry_canonical_dict, generated_registry_sha256

    s = LemmaSettings()
    reg_sha = generated_registry_sha256()
    prof = judge_profile_dict(s)
    prof_sha = judge_profile_sha256(s)

    if raw:
        reg = generated_registry_canonical_dict()
        click.echo(f"lemma_version={__version__}")
        click.echo(f"problem_source={s.problem_source}")
        click.echo(f"generated_registry_sha256={reg_sha}")
        click.echo("generated_registry_json=" + json.dumps(reg, sort_keys=True))
        click.echo(f"validator_profile_sha256={prof_sha}")
        click.echo("validator_profile_json=" + json.dumps(prof, sort_keys=True))
        return

    click.echo(stylize("Subnet fingerprints", fg="cyan", bold=True))
    click.echo(stylize("Prints canonical hashes only; it does not edit `.env`.\n", dim=True), nl=False)
    click.echo(stylize("\nRelease\n", fg="cyan"))
    click.echo(f"  lemma_version     {__version__}")
    click.echo(f"  problem_source    {s.problem_source}")
    click.echo(stylize("\nGenerated problem registry\n", fg="cyan"))
    click.echo(stylize(f"  SHA256  {reg_sha}", dim=False))
    click.echo(stylize("\nValidator scoring profile (your environment)\n", fg="cyan"))
    click.echo(stylize(f"  SHA256  {prof_sha}", dim=False))
    click.echo(stylize("\nFull canonical JSON: lemma meta --raw", dim=True))


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
    click.echo(stylize("Would use", fg="cyan", bold=True))
    click.echo(f"netuid={settings.netuid} axon_port={settings.axon_port}")
    ext = (settings.axon_external_ip or "").strip() or None
    if ext:
        click.echo(f"axon_external_ip={ext} (from AXON_EXTERNAL_IP)")
    elif settings.axon_discover_external_ip:
        from lemma.miner.public_ip import discover_public_ipv4

        discovered = discover_public_ipv4()
        if discovered:
            click.echo(f"axon_external_ip={discovered} (auto-discovered at startup)")
        else:
            click.echo(
                "axon_external_ip=<discovery failed; set AXON_EXTERNAL_IP to your public IPv4 "
                f"and ensure port {settings.axon_port} is reachable>",
            )
    else:
        click.echo("axon_external_ip=<unset; set AXON_EXTERNAL_IP or enable AXON_DISCOVER_EXTERNAL_IP>")
    click.echo("")
    click.echo(
        stylize(
            "Next: lemma miner start — bind port and wait for validators; "
            "lemma miner observability — explain logs and on-chain signals.",
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
    help="Miner axon — receive validator forwards and run the prover LLM.",
)
@click.option(
    "--max-forwards-per-day",
    type=int,
    default=None,
    help="Cap prover forwards per UTC day. Overrides MINER_MAX_FORWARDS_PER_DAY.",
)
@click.pass_context
def miner_group(ctx: click.Context, max_forwards_per_day: int | None) -> None:
    """Use explicit subcommands from scripts."""
    if ctx.invoked_subcommand is not None:
        return
    if max_forwards_per_day is not None:
        _miner_run_axon(max_forwards_per_day)
        return
    click.echo(ctx.get_help(), color=colors_enabled())
    click.echo("Use `lemma miner start`, `lemma miner dry-run`, or `lemma miner observability`.")


@miner_group.command("start", help="Listen on AXON_PORT for validator forwards. Press Ctrl+C to stop.")
@click.option(
    "--max-forwards-per-day",
    type=int,
    default=None,
    help="Cap successful forwards per UTC day. 0=unlimited. Overrides MINER_MAX_FORWARDS_PER_DAY.",
)
def miner_start_cmd(max_forwards_per_day: int | None) -> None:
    _miner_run_axon(max_forwards_per_day)


@miner_group.command("dry-run", help="Print axon / env summary only — does not bind the port.")
def miner_dry_run_cmd() -> None:
    _miner_emit_dry_run_summary()


@miner_group.command("observability", help="Explain miner logs vs validator scores and on-chain incentives.")
def miner_observability_cmd() -> None:
    from lemma.cli.miner_observability import print_miner_observability

    print_miner_observability()


def _validator_run_blocking(*, dry_run: bool) -> None:
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    ValidatorService(settings, dry_run=dry_run).run_blocking()


@main.group(
    "validator",
    invoke_without_command=True,
    help="Validator — query miners, Lean verify, proof-score, optional set_weights.",
)
@click.pass_context
def validator_group(ctx: click.Context) -> None:
    """Use explicit subcommands from scripts."""
    if ctx.invoked_subcommand is not None:
        return
    click.echo(ctx.get_help(), color=colors_enabled())
    click.echo(
        "Use `lemma validator start`, `lemma validator dry-run`, "
        "`lemma validator check`, or `lemma validator config`.",
    )


@validator_group.command("start", help="Run scoring rounds until Ctrl+C.")
def validator_start_cmd() -> None:
    _validator_run_blocking(dry_run=False)


@validator_group.command("dry-run", help="Full proof-verification scoring epochs without set_weights.")
def validator_dry_run_cmd() -> None:
    _validator_run_blocking(dry_run=True)


@validator_group.command("config", help="Print validator env summary and exit.")
def validator_config_cmd() -> None:
    from lemma.cli.validator_config import print_validator_config

    print_validator_config()


@validator_group.command("check", help="Pre-flight: chain, wallet UID, profile pins, Lean image.")
def validator_check_group_cmd() -> None:
    from lemma.cli.validator_check import run_validator_check

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    raise SystemExit(run_validator_check(settings))


@validator_group.command(
    "profile-attest-serve",
    help=(
        "Tiny HTTP server: GET /lemma/validator_profile_sha256. "
        "Pair with LEMMA_VALIDATOR_PROFILE_ATTEST_PEER_URLS on other validators."
    ),
)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8799, type=int, show_default=True)
def validator_profile_attest_serve_cmd(host: str, port: int) -> None:
    """Expose local validator profile hash for peer probes."""
    from lemma.validator.judge_profile_attest import serve_judge_profile_attest_forever

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    serve_judge_profile_attest_forever(host, port, settings)


@main.command("verify")
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
    help="Path to a Submission.lean file. Example: ./my_proof.lean",
)
@click.option(
    "--host-lean",
    "host_lean",
    is_flag=True,
    default=False,
    help="Run lake on host. Requires LEMMA_ALLOW_HOST_LEAN=1. Default is Docker.",
)
def verify_cmd(problem_id: str, submission_path: Path, host_lean: bool) -> None:
    """Verify a Submission.lean file against a catalog problem."""
    from lemma.lean.verify_runner import run_lean_verify

    settings = LemmaSettings()
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException(
            "Host Lean is disabled. Use Docker (default) to match validators. "
            "Set LEMMA_ALLOW_HOST_LEAN=1 in `.env` for local debugging, then use --host-lean.",
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
    """Run HTTP Lean verify worker (POST /verify); pair with LEMMA_LEAN_VERIFY_REMOTE_URL."""
    from lemma.lean.worker_http import serve_forever

    setup_logging(LemmaSettings().log_level)
    serve_forever(host, port)
