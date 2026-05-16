"""Lemma CLI.

Top-level imports stay light: the console script is named ``lemma``, and importing
``bittensor`` at module load would register global argparse handlers that steal ``--help``.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import click

from lemma import __version__
from lemma.cli.style import colors_enabled, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import resolve_problem

_PUBLIC_COMMAND_ORDER = ("setup", "config", "status", "theorem", "proof", "miner", "validator", "bounty")


class LemmaGroup(click.Group):
    def list_commands(self, ctx: click.Context) -> list[str]:
        public = [
            name
            for name in _PUBLIC_COMMAND_ORDER
            if name in self.commands and not getattr(self.commands[name], "hidden", False)
        ]
        other = sorted(
            name
            for name, command in self.commands.items()
            if name not in public and not getattr(command, "hidden", False)
        )
        return public + other


@click.group(
    name="lemma",
    cls=LemmaGroup,
    invoke_without_command=True,
    context_settings={"max_content_width": 100},
)
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Machine-checked formal proofs on Bittensor."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


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


def _present(value: str | None) -> bool:
    return bool(value and str(value).strip())


def _maybe_run_setup_for_missing_env(role: str) -> None:
    env_path = _env_path(None)
    if env_path.exists():
        return
    if not sys.stdin.isatty():
        raise click.ClickException(f"No .env found. Run `lemma setup --role {role}` first.")
    from lemma.cli.env_wizard import run_setup

    click.echo(stylize(f"No .env found. Starting {role} setup first.", fg="yellow", bold=True))
    run_setup(env_path, role)


def _miner_settings(*, coldkey: str | None, hotkey: str | None, port: int | None) -> LemmaSettings:
    settings = LemmaSettings()
    updates: dict[str, object] = {}
    if coldkey:
        updates["wallet_cold"] = coldkey
    if hotkey:
        updates["wallet_hot"] = hotkey
    if port is not None:
        updates["axon_port"] = port
    return settings.model_copy(update=updates) if updates else settings


def _run_miner_preflight(settings: LemmaSettings, *, start_after: bool) -> int:
    click.echo(stylize("Miner pre-flight", fg="cyan", bold=True))
    fatal: list[str] = []
    warn: list[str] = []

    provider = (settings.prover_provider or "anthropic").strip().lower()
    if provider == "openai":
        model = settings.prover_model or settings.openai_model
        if not _present(settings.prover_openai_api_key_resolved()):
            fatal.append("Missing prover API key. Run `lemma setup` or set PROVER_OPENAI_API_KEY.")
        if not _present(model):
            fatal.append("Missing prover model. Run `lemma setup` or set PROVER_MODEL.")
    elif provider == "anthropic":
        model = settings.prover_model or settings.anthropic_model
        if not _present(settings.anthropic_api_key):
            fatal.append("Missing Anthropic API key. Run `lemma setup` or set ANTHROPIC_API_KEY.")
        if not _present(model):
            fatal.append("Missing prover model. Run `lemma setup` or set PROVER_MODEL.")
    else:
        fatal.append(f"Unsupported PROVER_PROVIDER={provider!r}. Run `lemma setup` to choose a supported prover.")

    hk = None
    try:
        import bittensor as bt

        wallet = bt.Wallet(name=settings.wallet_cold, hotkey=settings.wallet_hot)
        hk = wallet.hotkey.ss58_address
        click.echo(stylize(f"OK wallet    cold={settings.wallet_cold!r} hot={settings.wallet_hot!r}", fg="green"))
    except Exception as e:  # noqa: BLE001
        fatal.append(f"Wallet not ready: {e}")

    try:
        from lemma.common.subtensor import get_subtensor

        subtensor = get_subtensor(settings)
        head = int(subtensor.get_current_block())
        click.echo(stylize(f"OK chain RPC  head_block={head}", fg="green"))
        if hk:
            uid = subtensor.get_uid_for_hotkey_on_subnet(hk, settings.netuid)
            if uid is None:
                fatal.append(
                    f"Hotkey is not registered on subnet netuid={settings.netuid}. "
                    "Register with btcli before mining.",
                )
            else:
                click.echo(stylize(f"OK subnet UID  {uid} on netuid={settings.netuid}", fg="green"))
    except Exception as e:  # noqa: BLE001
        fatal.append(f"Chain RPC failed: {e}")

    if not _present(settings.axon_external_ip) and not settings.axon_discover_external_ip:
        warn.append(
            "AXON_EXTERNAL_IP is unset. This is fine locally, but production miners need reachable axon IP/port."
        )

    if warn:
        click.echo("")
        click.echo(stylize("WARNINGS", fg="yellow", bold=True))
        for msg in warn:
            click.echo(stylize(f"  • {msg}", fg="yellow"), err=True)
    if fatal:
        click.echo("")
        click.echo(stylize("BLOCKING", fg="red", bold=True))
        for msg in fatal:
            click.echo(stylize(f"  • {msg}", fg="red"), err=True)
        click.echo(
            stylize(
                "\nNOT READY — fix blocking items, then run `lemma miner check` again.",
                fg="red",
                bold=True,
            )
        )
        return 1

    click.echo("")
    click.echo(stylize("READY", fg="green", bold=True))
    if start_after:
        click.echo(stylize("  Starting miner. Press Ctrl+C to stop.", dim=True))
    else:
        click.echo(stylize("  Next: lemma miner start", dim=True))
    return 0


def _run_validator_preflight(*, start_after: bool, dry_run: bool = False) -> int:
    from lemma.cli.validator_check import run_validator_check

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    if start_after:
        ready_next = (
            "Starting validator dry-run. Press Ctrl+C to stop."
            if dry_run
            else "Starting validator. Press Ctrl+C to stop."
        )
    else:
        ready_next = "Next: lemma validator start"
    return run_validator_check(settings, ready_next=ready_next)


@main.command("setup")
@click.option(
    "--role",
    type=click.Choice(["miner", "validator", "both"]),
    default="miner",
    show_default=True,
    help="What to configure.",
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

    run_setup(_env_path(env_path), role or "miner")


@main.group("config", invoke_without_command=True, help="Configure `.env` and inspect local readiness.")
@click.pass_context
def config_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@config_group.command("chain")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def config_chain_cmd(env_path: Path | None) -> None:
    """Set Bittensor testnet chain, endpoint, and wallet names."""
    from lemma.cli.env_wizard import collect_chain_updates

    _merge_env(env_path, collect_chain_updates)


@config_group.command("axon")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def config_axon_cmd(env_path: Path | None) -> None:
    """Set AXON_PORT for miners."""
    from lemma.cli.env_wizard import collect_axon_updates

    _merge_env(env_path, collect_axon_updates)


@config_group.command("lean-image")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def config_lean_image_cmd(env_path: Path | None) -> None:
    """Write the subnet Lean sandbox image name."""
    from lemma.cli.env_wizard import collect_lean_image_updates

    _merge_env(env_path, collect_lean_image_updates)


@config_group.command("prover")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def config_prover_cmd(env_path: Path | None) -> None:
    """Set miner prover LLM settings."""
    from lemma.cli.env_wizard import collect_prover_updates

    _merge_env(env_path, collect_prover_updates)
    click.echo("Done. Run `lemma miner dry-run` to confirm axon settings.")


@config_group.command("prover-model")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def config_prover_model_cmd(env_path: Path | None) -> None:
    """Set PROVER_MODEL only."""
    from lemma.cli.env_wizard import collect_prover_model_updates

    _merge_env(env_path, collect_prover_model_updates)
    click.echo("Done. Run `lemma config doctor` or `lemma proof preview` to confirm.")


@config_group.command("prover-retries")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
def config_prover_retries_cmd(env_path: Path | None) -> None:
    """Set prover retry attempts."""
    from lemma.cli.env_wizard import collect_prover_retries_updates

    _merge_env(env_path, collect_prover_retries_updates)
    click.echo("Done. Miner and `lemma proof preview` pick this up on next run.")


@config_group.command("subnet-pins")
@click.option("--env-file", "env_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
def config_subnet_pins_cmd(env_path: Path | None, yes: bool) -> None:
    """Write expected subnet hash pins from the current Lemma checkout."""
    from lemma.cli.env_file import merge_dotenv
    from lemma.cli.env_wizard import collect_subnet_pin_updates

    path = _env_path(env_path)
    updates = collect_subnet_pin_updates(LemmaSettings())
    click.echo("")
    click.echo(stylize("Config — subnet pins", fg="cyan", bold=True))
    click.echo("Will write")
    for key, value in updates.items():
        click.echo(stylize(f"  {key}=", fg="yellow", bold=True) + stylize(value, fg="green"))
    click.echo("")
    if not yes:
        click.confirm(f"Merge these lines into {path}?", abort=True)
    click.echo(stylize(f"Merging into {path}", dim=True))
    merge_dotenv(path, updates)
    click.echo(stylize("Done — pins saved.", fg="green", bold=True))


@config_group.command("doctor")
def config_doctor_cmd() -> None:
    """Check local environment, config, keys, and optional chain RPC."""
    from lemma.cli.doctor import run_doctor

    raise SystemExit(run_doctor())


def _run_meta(raw: bool) -> None:
    from lemma.judge.profile import judge_profile_dict, judge_profile_sha256
    from lemma.problems.generated import generated_registry_canonical_dict, generated_registry_sha256
    from lemma.problems.hybrid import problem_supply_registry_canonical_dict, problem_supply_registry_sha256

    s = LemmaSettings()
    reg_sha = generated_registry_sha256()
    supply_sha = problem_supply_registry_sha256(
        generated_weight=s.lemma_hybrid_generated_weight,
        catalog_weight=s.lemma_hybrid_catalog_weight,
    )
    prof = judge_profile_dict(s)
    prof_sha = judge_profile_sha256(s)

    if raw:
        reg = generated_registry_canonical_dict()
        supply = problem_supply_registry_canonical_dict(
            generated_weight=s.lemma_hybrid_generated_weight,
            catalog_weight=s.lemma_hybrid_catalog_weight,
        )
        click.echo(f"lemma_version={__version__}")
        click.echo(f"problem_source={s.problem_source}")
        click.echo(f"problem_supply_registry_sha256={supply_sha}")
        click.echo("problem_supply_registry_json=" + json.dumps(supply, sort_keys=True))
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
    click.echo(stylize("\nHybrid problem supply registry\n", fg="cyan"))
    click.echo(stylize(f"  SHA256  {supply_sha}", dim=False))
    click.echo(stylize("\nGenerated problem registry\n", fg="cyan"))
    click.echo(stylize(f"  SHA256  {reg_sha}", dim=False))
    click.echo(stylize("\nValidator scoring profile (your environment)\n", fg="cyan"))
    click.echo(stylize(f"  SHA256  {prof_sha}", dim=False))
    click.echo(stylize("\nFull canonical JSON: lemma config meta --raw", dim=True))


@config_group.command("meta")
@click.option("--raw", is_flag=True, help="Compact key=value lines.")
def config_meta_cmd(raw: bool) -> None:
    """Canonical fingerprints: problem supply + validator scoring profile."""
    _run_meta(raw)


@main.group("configure", hidden=True, invoke_without_command=True)
@click.pass_context
def configure_group(ctx: click.Context) -> None:
    """Compatibility alias for `lemma config`."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


for _name, _command in config_group.commands.items():
    configure_group.add_command(_command, _name)


@main.command("doctor", hidden=True)
def doctor_cmd() -> None:
    """Check local environment; compatibility alias for `lemma config doctor`."""
    from lemma.cli.doctor import run_doctor

    raise SystemExit(run_doctor())


@main.command("meta", hidden=True)
@click.option("--raw", is_flag=True, help="Compact key=value lines.")
def meta_cmd(raw: bool) -> None:
    """Compatibility alias for `lemma config meta`."""
    _run_meta(raw)


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
    click.echo(f"  {stylize('lemma theorem current', fg='green')}  " + stylize("print Challenge.lean", dim=True))
    click.echo(f"  {stylize('lemma miner check', fg='green')}      " + stylize("check miner readiness", dim=True))
    click.echo(f"  {stylize('lemma validator check', fg='green')}  " + stylize("check validator readiness", dim=True))


def _theorem_show(problem_id: str | None, current: bool, block: int | None) -> None:
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
        raise click.UsageError("Give at most one of: PROBLEM_ID, --current, or --block N.")

    ctx = click.get_current_context(silent=True)
    command_path = ctx.command_path if ctx is not None else "lemma theorem show"
    if current or block is not None:
        subtensor = get_subtensor(settings)
        head = int(subtensor.get_current_block()) if current else int(block or 0)
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
        click.echo(stylize(command_path, fg="cyan", bold=True))
        click.echo(stylize(f"chain_head={head}  problem_seed_chain_head={seed_head}  problem_seed={seed}\n", dim=True))
        echo_next_theorem_countdown(settings, chain_head_block=seed_head, seed_tag=tag, subtensor=subtensor)
        echo_problem_card(p, heading="Theorem")
        echo_challenge_separator()
        click.echo(p.challenge_source())
        return

    if problem_id is None:
        raise click.UsageError("problem_id is required unless using --current or --block.")
    p = resolve_problem(settings, problem_id.strip())
    click.echo(stylize(f"{command_path} {problem_id.strip()}", fg="cyan", bold=True))
    click.echo("")
    echo_problem_card(p, heading="Theorem")
    echo_challenge_separator()
    click.echo(p.challenge_source())


@main.group("theorem", invoke_without_command=True, help="Inspect current and catalog theorem targets.")
@click.pass_context
def theorem_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@theorem_group.command("current")
def theorem_current_cmd() -> None:
    """Print the current chain theorem Challenge.lean."""
    _theorem_show(None, True, None)


@theorem_group.command("show", context_settings={"max_content_width": 100})
@click.argument("problem_id", required=False)
@click.option("--current", "-c", is_flag=True, help="Use current chain head + LEMMA_PROBLEM_SEED_MODE.")
@click.option("--block", type=int, default=None, help="Treat N as chain head height; resolve seed like validators.")
def theorem_show_cmd(problem_id: str | None, current: bool, block: int | None) -> None:
    """Print Challenge.lean source for one theorem."""
    _theorem_show(problem_id, current, block)


@theorem_group.command("list")
def theorem_list_cmd() -> None:
    """List frozen catalog theorems, when the active source is enumerable."""
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


@main.group("problems", hidden=True, invoke_without_command=True)
@click.pass_context
def problems_group(ctx: click.Context) -> None:
    """Compatibility alias for `lemma theorem`."""
    if ctx.invoked_subcommand is None:
        _theorem_show(None, True, None)


problems_group.add_command(theorem_list_cmd, "list")
problems_group.add_command(theorem_show_cmd, "show")


def _run_preview(
    *,
    do_verify: bool,
    block: int | None,
    assume_yes: bool,
    retry_attempts: int | None,
    host_lean: bool,
    docker_verify: bool,
) -> None:
    from lemma.cli.preview import assert_preview_host_lean_allowed, run_preview

    ctx = click.get_current_context(silent=True)
    label = ctx.command_path if ctx is not None else "lemma proof preview"
    if not assume_yes:
        _confirm_cost(label)
    settings = LemmaSettings()
    assert_preview_host_lean_allowed(settings, verify=do_verify, host_lean=host_lean)
    run_preview(
        settings,
        verify=do_verify,
        block=block,
        prover_llm_retry_attempts=retry_attempts,
        lean_use_docker=_resolve_lean_backend(host_lean, docker_verify),
    )


def _run_proof_verify(problem_id: str, submission_path: Path, host_lean: bool) -> None:
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
    raise SystemExit(0 if vr.passed else 1)


@main.group("proof", invoke_without_command=True, help="Preview prover output and verify Submission.lean files.")
@click.pass_context
def proof_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@proof_group.command("preview")
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
def proof_preview_cmd(
    do_verify: bool,
    block: int | None,
    assume_yes: bool,
    retry_attempts: int | None,
    host_lean: bool,
    docker_verify: bool,
) -> None:
    """Live theorem -> prover -> optional Lean proof preview."""
    _run_preview(
        do_verify=do_verify,
        block=block,
        assume_yes=assume_yes,
        retry_attempts=retry_attempts,
        host_lean=host_lean,
        docker_verify=docker_verify,
    )


@proof_group.command("verify")
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
    help="Path to a Submission.lean file.",
)
@click.option(
    "--host-lean",
    "host_lean",
    is_flag=True,
    default=False,
    help="Run lake on host. Requires LEMMA_ALLOW_HOST_LEAN=1. Default is Docker.",
)
def proof_verify_cmd(problem_id: str, submission_path: Path, host_lean: bool) -> None:
    """Verify a Submission.lean file against a catalog theorem."""
    _run_proof_verify(problem_id, submission_path, host_lean)


@main.command("preview", hidden=True)
@click.option("--verify/--no-verify", "do_verify", default=True, help="After the prover answers, run Lean verify.")
@click.option("--block", type=int, default=None, help="Pretend chain head is this block.")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip the API-cost prompt.")
@click.option("--retry-attempts", "retry_attempts", type=click.IntRange(1, 32), default=None)
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
    """Compatibility alias for `lemma proof preview`."""
    _run_preview(
        do_verify=do_verify,
        block=block,
        assume_yes=assume_yes,
        retry_attempts=retry_attempts,
        host_lean=host_lean,
        docker_verify=docker_verify,
    )


@main.command("verify", hidden=True)
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
    help="Path to a Submission.lean file.",
)
@click.option("--host-lean", "host_lean", is_flag=True, default=False)
def verify_cmd(problem_id: str, submission_path: Path, host_lean: bool) -> None:
    """Compatibility alias for `lemma proof verify`."""
    _run_proof_verify(problem_id, submission_path, host_lean)


def _miner_apply_daily_cap(max_forwards_per_day: int | None) -> None:
    if max_forwards_per_day is not None:
        os.environ["MINER_MAX_FORWARDS_PER_DAY"] = str(max_forwards_per_day)


def _miner_emit_dry_run_summary(settings: LemmaSettings) -> None:
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
    click.echo(f"wallet={settings.wallet_cold}/{settings.wallet_hot}")
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


def _miner_run_axon(settings: LemmaSettings, max_forwards_per_day: int | None) -> None:
    from lemma.miner.service import MinerService

    _miner_apply_daily_cap(max_forwards_per_day)
    setup_logging(settings.log_level)
    MinerService(settings).run()


def _run_miner_command(
    *,
    check: bool,
    coldkey: str | None,
    hotkey: str | None,
    port: int | None,
    max_forwards_per_day: int | None,
) -> None:
    _maybe_run_setup_for_missing_env("miner")
    try:
        settings = _miner_settings(coldkey=coldkey, hotkey=hotkey, port=port)
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(f"Could not load Lemma config: {e}") from e
    rc = _run_miner_preflight(settings, start_after=not check)
    if rc != 0:
        raise SystemExit(rc)
    if check:
        return
    _miner_run_axon(settings, max_forwards_per_day)


@main.group("miner", invoke_without_command=True, help="Run and inspect the miner axon.")
@click.pass_context
def miner_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


def _miner_identity_options(fn):
    fn = click.option("--port", type=int, default=None, help="Axon port for this run. Default: AXON_PORT.")(fn)
    fn = click.option("--hotkey", default=None, help="Hotkey name for this run. Default: BT_WALLET_HOT.")(fn)
    fn = click.option("--coldkey", default=None, help="Cold wallet name for this run. Default: BT_WALLET_COLD.")(fn)
    return fn


@miner_group.command("check", help="Run miner setup checks only.")
@_miner_identity_options
def miner_check_cmd(coldkey: str | None, hotkey: str | None, port: int | None) -> None:
    _run_miner_command(
        check=True,
        coldkey=coldkey,
        hotkey=hotkey,
        port=port,
        max_forwards_per_day=None,
    )


@miner_group.command("start", help="Check setup, then listen on AXON_PORT. Press Ctrl+C to stop.")
@_miner_identity_options
@click.option(
    "--max-forwards-per-day",
    type=int,
    default=None,
    help="Cap successful forwards per UTC day. 0=unlimited. Overrides MINER_MAX_FORWARDS_PER_DAY.",
)
def miner_start_cmd(
    coldkey: str | None,
    hotkey: str | None,
    port: int | None,
    max_forwards_per_day: int | None,
) -> None:
    _run_miner_command(
        check=False,
        coldkey=coldkey,
        hotkey=hotkey,
        port=port,
        max_forwards_per_day=max_forwards_per_day,
    )


@miner_group.command("dry-run", help="Print axon / env summary only; does not bind the port.")
@_miner_identity_options
def miner_dry_run_cmd(coldkey: str | None, hotkey: str | None, port: int | None) -> None:
    _miner_emit_dry_run_summary(_miner_settings(coldkey=coldkey, hotkey=hotkey, port=port))


@miner_group.command("observability", help="Explain miner logs vs validator scores and on-chain incentives.")
def miner_observability_cmd() -> None:
    from lemma.cli.miner_observability import print_miner_observability

    print_miner_observability()


@main.command("mine", hidden=True)
@click.option("--check", is_flag=True, help="Run setup checks only; do not start the miner.")
@_miner_identity_options
@click.option(
    "--max-forwards-per-day",
    type=int,
    default=None,
    help="Cap prover forwards per UTC day. Overrides MINER_MAX_FORWARDS_PER_DAY.",
)
def mine_cmd(
    check: bool,
    coldkey: str | None,
    hotkey: str | None,
    port: int | None,
    max_forwards_per_day: int | None,
) -> None:
    """Compatibility alias for `lemma miner start`."""
    _run_miner_command(
        check=check,
        coldkey=coldkey,
        hotkey=hotkey,
        port=port,
        max_forwards_per_day=max_forwards_per_day,
    )


def _validator_run_blocking(*, dry_run: bool) -> None:
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    ValidatorService(settings, dry_run=dry_run).run_blocking()


def _run_validator_command(*, check: bool, dry_run: bool) -> None:
    _maybe_run_setup_for_missing_env("validator")
    rc = _run_validator_preflight(start_after=not check, dry_run=dry_run)
    if rc != 0:
        raise SystemExit(rc)
    if check:
        return
    _validator_run_blocking(dry_run=dry_run)


@main.group("validator", invoke_without_command=True, help="Run validator rounds and validator-side tools.")
@click.pass_context
def validator_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@validator_group.command("check", help="Pre-flight: chain, wallet UID, profile pins, Lean image.")
def validator_check_group_cmd() -> None:
    _run_validator_command(check=True, dry_run=False)


@validator_group.command("start", help="Check setup, then run scoring rounds until Ctrl+C.")
def validator_start_cmd() -> None:
    _run_validator_command(check=False, dry_run=False)


@validator_group.command("dry-run", help="Full proof-verification scoring epochs without set_weights.")
def validator_dry_run_cmd() -> None:
    _run_validator_command(check=False, dry_run=True)


@validator_group.command("config", help="Print validator env summary and exit.")
def validator_config_cmd() -> None:
    from lemma.cli.validator_config import print_validator_config

    print_validator_config()


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


def _run_lean_worker(host: str, port: int) -> None:
    from lemma.lean.worker_http import lean_worker_bind_error, serve_forever

    settings = LemmaSettings()
    err = lean_worker_bind_error(host, settings)
    if err:
        raise click.ClickException(err)
    setup_logging(settings.log_level)
    serve_forever(host, port, settings)


@validator_group.command("lean-worker", help="Run HTTP Lean verify worker (POST /verify).")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8787, type=int, show_default=True)
def validator_lean_worker_cmd(host: str, port: int) -> None:
    _run_lean_worker(host, port)


@main.command("validate", hidden=True)
@click.option("--check", is_flag=True, help="Run validator pre-flight only; do not start validation.")
@click.option("--dry-run", is_flag=True, help="Run validator rounds without set_weights.")
def validate_cmd(check: bool, dry_run: bool) -> None:
    """Compatibility alias for `lemma validator start`."""
    _run_validator_command(check=check, dry_run=dry_run)


@main.command("lean-worker", hidden=True)
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8787, type=int, show_default=True)
def lean_worker_cmd(host: str, port: int) -> None:
    """Compatibility alias for `lemma validator lean-worker`."""
    _run_lean_worker(host, port)


def _load_bounty_registry():
    from lemma.bounty.client import BountyError, fetch_registry

    try:
        return fetch_registry(LemmaSettings())
    except (BountyError, OSError) as e:
        raise click.ClickException(str(e)) from e


def _bounty_or_die(bounty_id: str):
    from lemma.bounty.client import BountyError

    registry = _load_bounty_registry()
    try:
        return registry, registry.get(bounty_id)
    except BountyError as e:
        raise click.ClickException(str(e)) from e


def _read_submission(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _verify_bounty_or_exit(bounty, submission_path: Path, host_lean: bool):
    from lemma.bounty.client import BountyError, verify_bounty_proof

    try:
        result = verify_bounty_proof(LemmaSettings(), bounty, _read_submission(submission_path), host_lean=host_lean)
    except BountyError as e:
        raise click.ClickException(str(e)) from e
    click.echo(result.model_dump_json(indent=2))
    raise SystemExit(0 if result.passed else 1)


@main.group("bounty", invoke_without_command=True, help="Browse, verify, package, and submit bounty proofs.")
@click.pass_context
def bounty_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@bounty_group.command("list")
@click.option("--all", "show_all", is_flag=True, help="Show closed and draft bounties too.")
def bounty_list_cmd(show_all: bool) -> None:
    """List bounties from the remote registry."""
    registry = _load_bounty_registry()
    rows = [b for b in registry.bounties if show_all or b.status == "open"]
    click.echo(stylize("Lemma bounties", fg="cyan", bold=True))
    click.echo(stylize(f"registry_sha256={registry.sha256}", dim=True))
    if not rows:
        click.echo("No open bounties.")
        return
    for bounty in rows:
        reward = f"  reward={bounty.reward}" if bounty.reward else ""
        deadline = f"  deadline={bounty.deadline}" if bounty.deadline else ""
        click.echo(f"{bounty.id}\t{bounty.status}\t{bounty.title}{reward}{deadline}")


@bounty_group.command("show")
@click.argument("bounty_id")
def bounty_show_cmd(bounty_id: str) -> None:
    """Show one bounty target and terms."""
    registry, bounty = _bounty_or_die(bounty_id)
    source_name = bounty.source.get("name") or bounty.source.get("project") or "unknown"
    source_url = bounty.source.get("url")
    click.echo(stylize(bounty.title, fg="cyan", bold=True))
    click.echo(stylize(f"id={bounty.id}  status={bounty.status}  registry_sha256={registry.sha256}", dim=True))
    if bounty.reward:
        click.echo(f"reward: {bounty.reward}")
    if bounty.deadline:
        click.echo(f"deadline: {bounty.deadline}")
    if bounty.terms_url:
        click.echo(f"terms: {bounty.terms_url}")
    click.echo(f"source: {source_name}" + (f" ({source_url})" if source_url else ""))
    click.echo("")
    click.echo(stylize("Lean target", fg="cyan"))
    click.echo(f"  theorem_id:   {bounty.problem.id}")
    click.echo(f"  theorem_name: {bounty.problem.theorem_name}")
    click.echo(f"  split:        {bounty.problem.split}")
    click.echo("")
    click.echo(stylize("Next", fg="cyan"))
    click.echo(f"  lemma bounty verify {bounty.id} --submission Submission.lean")
    click.echo(f"  lemma bounty submit {bounty.id} --submission Submission.lean --payout <SS58>")


@bounty_group.command("verify")
@click.argument("bounty_id")
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
    help="Path to a Submission.lean file.",
)
@click.option("--host-lean", "host_lean", is_flag=True, default=False)
def bounty_verify_cmd(bounty_id: str, submission_path: Path, host_lean: bool) -> None:
    """Verify a bounty proof locally before packaging or submitting."""
    _, bounty = _bounty_or_die(bounty_id)
    _verify_bounty_or_exit(bounty, submission_path, host_lean)


def _bounty_package(
    *,
    bounty_id: str,
    submission_path: Path,
    wallet_cold: str | None,
    wallet_hot: str | None,
    payout: str,
    host_lean: bool,
) -> dict[str, object]:
    from lemma.bounty.client import BountyError, build_submission_package, verify_bounty_proof

    settings = LemmaSettings()
    registry, bounty = _bounty_or_die(bounty_id)
    proof_script = _read_submission(submission_path)
    try:
        result = verify_bounty_proof(settings, bounty, proof_script, host_lean=host_lean)
        if not result.passed:
            raise BountyError("proof failed Lean verification; not packaging")
        return build_submission_package(
            settings,
            registry=registry,
            bounty=bounty,
            proof_script=proof_script,
            wallet_cold=wallet_cold,
            wallet_hot=wallet_hot,
            payout_ss58=payout,
        )
    except BountyError as e:
        raise click.ClickException(str(e)) from e


@bounty_group.command("package")
@click.argument("bounty_id")
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
)
@click.option("--wallet-cold", default=None, help="Cold wallet name. Default: BT_WALLET_COLD.")
@click.option("--wallet-hot", default=None, help="Hotkey name. Default: BT_WALLET_HOT.")
@click.option("--payout", required=True, help="SS58 payout address.")
@click.option("--host-lean", "host_lean", is_flag=True, default=False)
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), default=None)
def bounty_package_cmd(
    bounty_id: str,
    submission_path: Path,
    wallet_cold: str | None,
    wallet_hot: str | None,
    payout: str,
    host_lean: bool,
    output_path: Path | None,
) -> None:
    """Verify, sign, and print or write a bounty submission package."""
    package = _bounty_package(
        bounty_id=bounty_id,
        submission_path=submission_path,
        wallet_cold=wallet_cold,
        wallet_hot=wallet_hot,
        payout=payout,
        host_lean=host_lean,
    )
    text = json.dumps(package, indent=2, sort_keys=True)
    if output_path is None:
        click.echo(text)
        return
    output_path.write_text(text + "\n", encoding="utf-8")
    click.echo(stylize(f"Wrote {output_path}", fg="green", bold=True))


@bounty_group.command("submit")
@click.argument("bounty_id")
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, file_okay=True, path_type=Path),
    required=True,
)
@click.option("--wallet-cold", default=None, help="Cold wallet name. Default: BT_WALLET_COLD.")
@click.option("--wallet-hot", default=None, help="Hotkey name. Default: BT_WALLET_HOT.")
@click.option("--payout", required=True, help="SS58 payout address.")
@click.option("--host-lean", "host_lean", is_flag=True, default=False)
def bounty_submit_cmd(
    bounty_id: str,
    submission_path: Path,
    wallet_cold: str | None,
    wallet_hot: str | None,
    payout: str,
    host_lean: bool,
) -> None:
    """Verify, sign, and POST a bounty proof to the Lemma API."""
    from lemma.bounty.client import BountyError, submit_submission_package

    package = _bounty_package(
        bounty_id=bounty_id,
        submission_path=submission_path,
        wallet_cold=wallet_cold,
        wallet_hot=wallet_hot,
        payout=payout,
        host_lean=host_lean,
    )
    try:
        response = submit_submission_package(LemmaSettings(), package)
    except BountyError as e:
        raise click.ClickException(str(e)) from e
    click.echo(json.dumps(response, indent=2, sort_keys=True))
