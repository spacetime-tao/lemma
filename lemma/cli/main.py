"""Lemma CLI.

Top-level imports stay light: the console script is named ``lemma``, and importing
``bittensor`` at module load would register global argparse handlers that steal ``--help``.
"""

from __future__ import annotations

import json
import os
import secrets
import sys
from pathlib import Path

import click

from lemma import __version__
from lemma.cli.style import colors_enabled, rich_help_text, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import resolve_problem

_PUBLIC_COMMAND_ORDER = ("setup", "mine", "status", "validate")


class LemmaCommand(click.Command):
    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rich_help = rich_help_text(self, ctx)
        if rich_help is None:
            super().format_help(ctx, formatter)
            return
        formatter.write(rich_help)


class LemmaGroup(click.Group):
    command_class = LemmaCommand
    group_class = type

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rich_help = rich_help_text(self, ctx)
        if rich_help is None:
            super().format_help(ctx, formatter)
            return
        formatter.write(rich_help)

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


@main.group("config", hidden=True, invoke_without_command=True, help="Configure `.env` and inspect local readiness.")
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
    """Show escrow-backed bounty market status."""
    from lemma.bounty.client import BountyError, fetch_registry

    settings = LemmaSettings()
    click.echo(stylize("Lemma bounty market", fg="cyan", bold=True))
    click.echo(stylize("Live rewards require trustless Bittensor EVM escrow.\n", dim=True), nl=False)
    click.echo(stylize("Custody", fg="cyan"))
    click.echo(stylize("  reward_custody ", dim=True) + settings.bounty_reward_custody)
    click.echo(stylize("  evm_chain_id   ", dim=True) + str(settings.bounty_evm_chain_id))
    click.echo(stylize("  evm_rpc_url    ", dim=True) + settings.bounty_evm_rpc_url)
    escrow_contract = (settings.bounty_escrow_contract_address or "").strip()
    click.echo(
        stylize("  escrow_contract", dim=True)
        + (f" {escrow_contract}" if escrow_contract else " not configured"),
    )
    if settings.bounty_reward_custody != "evm_escrow":
        click.echo(stylize("  local_dry_run is not live reward custody", fg="yellow", bold=True))

    click.echo("")
    try:
        registry = fetch_registry(settings)
    except (BountyError, OSError) as e:
        click.echo(stylize(f"Registry unavailable: {e}", fg="yellow"))
        click.echo(stylize("Next: set LEMMA_BOUNTY_REGISTRY_URL or try again when network is reachable.", dim=True))
        return

    escrow_rows = [b for b in registry.bounties if b.escrow_backed]
    candidates = [b for b in registry.bounties if not b.escrow_backed]
    click.echo(stylize("Registry", fg="cyan"))
    click.echo(stylize("  schema_version ", dim=True) + str(registry.schema_version))
    click.echo(stylize("  registry_sha256 ", dim=True) + registry.sha256)
    click.echo(stylize("  escrow_backed  ", dim=True) + str(len(escrow_rows)))
    click.echo(stylize("  candidates     ", dim=True) + str(len(candidates)))
    if escrow_rows:
        click.echo("")
        click.echo(stylize("Escrow-backed bounties", fg="cyan"))
        for bounty in escrow_rows:
            click.echo(
                f"  {stylize(bounty.id, fg='green', bold=True)} "
                f"contract={bounty.escrow_contract_address} escrow_id={bounty.escrow_bounty_id}",
            )
        return

    click.echo("")
    click.echo(stylize("No registry row is configured as escrow-backed yet.", fg="yellow", bold=True))
    if candidates:
        click.echo(
            stylize("Candidate targets are draft work until a funded escrow bounty is confirmed on-chain.", dim=True),
        )
        click.echo(stylize("Try: ", dim=True) + stylize(f"lemma mine {candidates[0].id}", fg="green"))


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


@main.group("theorem", hidden=True, invoke_without_command=True, help="Inspect current and catalog theorem targets.")
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


@main.group(
    "proof",
    hidden=True,
    invoke_without_command=True,
    help="Preview prover output and verify Submission.lean files.",
)
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


@main.group("miner", hidden=True, invoke_without_command=True, help="Run and inspect the miner axon.")
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


def _hotkey_public_key_hex(settings: LemmaSettings, wallet_cold: str | None, wallet_hot: str | None) -> str:
    import bittensor as bt

    wallet = bt.Wallet(name=wallet_cold or settings.wallet_cold, hotkey=wallet_hot or settings.wallet_hot)
    pub = getattr(wallet.hotkey, "public_key", None)
    if callable(pub):
        pub = pub()
    if isinstance(pub, bytes):
        return "0x" + pub.hex()
    raw = str(pub or "").strip()
    if raw.startswith("0x") and len(raw) == 66:
        return raw
    raise click.ClickException("Could not read the hotkey public key for escrow identity binding.")


def _sign_bounty_identity(
    settings: LemmaSettings,
    *,
    wallet_cold: str | None,
    wallet_hot: str | None,
    message: bytes,
) -> str:
    import bittensor as bt

    wallet = bt.Wallet(name=wallet_cold or settings.wallet_cold, hotkey=wallet_hot or settings.wallet_hot)
    return wallet.hotkey.sign(message).hex()


def _bounty_escrow_values(settings: LemmaSettings, bounty) -> tuple[int, str, int]:
    chain_id = bounty.escrow_chain_id or int(settings.bounty_evm_chain_id)
    contract = bounty.escrow_contract_address or (settings.bounty_escrow_contract_address or "").strip()
    escrow_bounty_id = bounty.escrow_bounty_id
    if not contract or escrow_bounty_id is None:
        raise click.ClickException(
            "This bounty is not escrow-backed. Live rewards require a funded LemmaBountyEscrow row.",
        )
    return int(chain_id), contract, int(escrow_bounty_id)


def _print_mine_intro(registry) -> None:
    escrow_rows = [b for b in registry.bounties if b.escrow_backed]
    candidate_rows = [b for b in registry.bounties if not b.escrow_backed]
    click.echo(stylize("Lemma mine", fg="cyan", bold=True))
    click.echo(
        stylize("Search any way you want. The reward path is the final Lean proof and escrow claim.\n", dim=True),
    )
    if escrow_rows:
        click.echo(stylize("Escrow-backed bounties", fg="cyan"))
        for bounty in escrow_rows:
            click.echo(f"  {stylize(bounty.id, fg='green', bold=True)}  {bounty.title}")
        click.echo(stylize("\nCheck one: ", dim=True) + stylize(f"lemma mine {escrow_rows[0].id}", fg="green"))
        return
    click.echo(stylize("No escrow-backed live bounties are in the registry yet.", fg="yellow", bold=True))
    if candidate_rows:
        click.echo(stylize("Draft candidates", fg="cyan"))
        for bounty in candidate_rows:
            click.echo(f"  {bounty.id}  {bounty.title}")
        click.echo(stylize("\nDraft targets are not live reward offers until escrow funding is on-chain.", dim=True))


@main.command("mine")
@click.argument("bounty_id", required=False)
@click.option("--submission", "submission_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--commit", "make_commit", is_flag=True, help="Build an escrow commit transaction package.")
@click.option("--reveal", "make_reveal", is_flag=True, help="Build an escrow reveal transaction package.")
@click.option(
    "--artifact-uri",
    default="",
    help="Public URI for the proof artifact; included in reveal package metadata.",
)
@click.option("--claimant-evm", default="", help="EVM address that will send the escrow transaction.")
@click.option("--payout-evm", default="", help="EVM address that receives the escrow payout.")
@click.option("--salt", default="", help="32-byte hex salt. Default: random for --commit.")
@click.option("--wallet-cold", default=None, help="Cold wallet name for hotkey identity binding.")
@click.option("--wallet-hot", default=None, help="Hotkey name for identity binding.")
@click.option("--host-lean", "host_lean", is_flag=True, default=False)
@click.option("--output", "output_path", type=click.Path(dir_okay=False, path_type=Path), default=None)
def mine_cmd(
    bounty_id: str | None,
    submission_path: Path | None,
    make_commit: bool,
    make_reveal: bool,
    artifact_uri: str,
    claimant_evm: str,
    payout_evm: str,
    salt: str,
    wallet_cold: str | None,
    wallet_hot: str | None,
    host_lean: bool,
    output_path: Path | None,
) -> None:
    """Guided path for escrow-backed theorem bounty claims."""
    from lemma.bounty.client import BountyError, fetch_registry, verify_bounty_proof
    from lemma.bounty.escrow import (
        BountyEscrowClient,
        EscrowError,
        bounty_identity_binding_message,
        build_commitment,
        bytes32_from_text,
        encode_commit_proof_call,
        encode_reveal_proof_call,
        proof_artifact_sha256,
    )

    if make_commit and make_reveal:
        raise click.UsageError("Use --commit or --reveal, not both.")
    settings = LemmaSettings()
    try:
        registry = fetch_registry(settings)
    except (BountyError, OSError) as e:
        raise click.ClickException(str(e)) from e
    if not bounty_id:
        _print_mine_intro(registry)
        return
    try:
        bounty = registry.get(bounty_id)
    except BountyError as e:
        raise click.ClickException(str(e)) from e

    chain_id, contract, escrow_bounty_id = _bounty_escrow_values(settings, bounty)
    click.echo(stylize(bounty.title, fg="cyan", bold=True))
    click.echo(stylize("  bounty_id       ", dim=True) + bounty.id)
    click.echo(stylize("  escrow_contract ", dim=True) + contract)
    click.echo(stylize("  escrow_bounty_id", dim=True) + str(escrow_bounty_id))
    click.echo(stylize("  target_sha256   ", dim=True) + bounty.target_sha256)

    if submission_path is None:
        click.echo("")
        click.echo(stylize("Next", fg="cyan"))
        click.echo("  " + stylize(f"lemma mine {bounty.id} --submission Submission.lean", fg="green"))
        return

    proof_script = _read_submission(submission_path)
    try:
        result = verify_bounty_proof(settings, bounty, proof_script, host_lean=host_lean)
    except BountyError as e:
        raise click.ClickException(str(e)) from e
    click.echo(result.model_dump_json(indent=2))
    if not result.passed:
        raise SystemExit(1)
    if not (make_commit or make_reveal):
        click.echo(
            stylize("Proof verifies locally. Add --commit or --reveal to build escrow transaction data.", fg="green"),
        )
        return

    if not claimant_evm or not payout_evm:
        raise click.UsageError("--claimant-evm and --payout-evm are required for escrow commit/reveal packages.")
    artifact_hash = "0x" + proof_artifact_sha256(submission_path)
    salt_hex = salt.strip() or "0x" + secrets.token_hex(32)
    try:
        hotkey_pubkey = _hotkey_public_key_hex(settings, wallet_cold, wallet_hot)
        commitment = build_commitment(
            bounty_id=bounty.id,
            chain_id=chain_id,
            contract_address=contract,
            escrow_bounty_id=escrow_bounty_id,
            theorem_id=bytes32_from_text(bounty.problem.id),
            claimant_evm_address=claimant_evm,
            payout_evm_address=payout_evm,
            artifact_sha256=artifact_hash,
            salt=salt_hex,
            toolchain_id=bytes32_from_text(bounty.toolchain_id),
            policy_version=bytes32_from_text(bounty.policy_version),
            registry_sha256="0x" + registry.sha256,
            submitter_hotkey_pubkey=hotkey_pubkey,
        )
        binding_msg = bounty_identity_binding_message(
            bounty_id=bounty.id,
            registry_sha256="0x" + registry.sha256,
            claimant_evm_address=claimant_evm,
            payout_evm_address=payout_evm,
            artifact_sha256=artifact_hash,
            commitment_hash_hex=commitment.commitment_hash,
        )
        signature_hex = _sign_bounty_identity(
            settings,
            wallet_cold=wallet_cold,
            wallet_hot=wallet_hot,
            message=binding_msg,
        )
    except EscrowError as e:
        raise click.ClickException(str(e)) from e

    package = commitment.as_dict()
    package["identity_binding_signature_hex"] = signature_hex
    package["artifact_uri"] = artifact_uri.strip()
    if make_commit:
        package["transaction"] = {
            "to": contract,
            "data": encode_commit_proof_call(escrow_bounty_id, commitment.commitment_hash),
            "value": "0x0",
        }
    else:
        package["transaction"] = {
            "to": contract,
            "data": encode_reveal_proof_call(
                escrow_bounty_id=escrow_bounty_id,
                commitment_hash_hex=commitment.commitment_hash,
                artifact_sha256=artifact_hash,
                salt=salt_hex,
                payout_evm_address=payout_evm,
                submitter_hotkey_pubkey=hotkey_pubkey,
            ),
            "value": "0x0",
        }
    if settings.bounty_escrow_contract_address:
        package["rpc_url"] = settings.bounty_evm_rpc_url
        package["client_transaction"] = BountyEscrowClient(
            rpc_url=settings.bounty_evm_rpc_url,
            contract_address=contract,
            timeout_s=settings.bounty_http_timeout_s,
        ).commit_transaction(
            escrow_bounty_id=escrow_bounty_id,
            commitment_hash_hex=commitment.commitment_hash,
        ) if make_commit else package["transaction"]

    text = json.dumps(package, indent=2, sort_keys=True)
    if output_path:
        output_path.write_text(text + "\n", encoding="utf-8")
        click.echo(stylize(f"Wrote {output_path}", fg="green", bold=True))
    else:
        click.echo(text)


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


@main.group(
    "validator",
    hidden=True,
    invoke_without_command=True,
    help="Run validator rounds and validator-side tools.",
)
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


@main.command("validate")
@click.option("--check", is_flag=True, help="Check bounty validator escrow configuration.")
@click.option("--once", is_flag=True, help="Run one bounty reveal scan when the watcher is configured.")
@click.option("--cadence", is_flag=True, hidden=True, help="Compatibility: run the old cadence validator.")
@click.option("--dry-run", is_flag=True, hidden=True, help="Compatibility with --cadence.")
def validate_cmd(check: bool, once: bool, cadence: bool, dry_run: bool) -> None:
    """Verify revealed bounty proofs and attest through escrow."""
    if cadence:
        _run_validator_command(check=check, dry_run=dry_run)
        return

    from lemma.bounty.client import BountyError, fetch_registry

    settings = LemmaSettings()
    click.echo(stylize("Lemma validate", fg="cyan", bold=True))
    click.echo(stylize("Validators verify Lean off-chain, then attest to the escrow contract.\n", dim=True), nl=False)
    if settings.bounty_reward_custody != "evm_escrow":
        raise click.ClickException("Live validation requires LEMMA_BOUNTY_REWARD_CUSTODY=evm_escrow.")
    if not (settings.bounty_escrow_contract_address or "").strip():
        raise click.ClickException("Set LEMMA_BOUNTY_ESCROW_CONTRACT_ADDRESS before validating live bounties.")
    try:
        registry = fetch_registry(settings)
    except (BountyError, OSError) as e:
        raise click.ClickException(str(e)) from e
    escrow_rows = [b for b in registry.bounties if b.escrow_backed]
    click.echo(stylize("Registry", fg="cyan"))
    click.echo(stylize("  registry_sha256 ", dim=True) + registry.sha256)
    click.echo(stylize("  escrow_rows     ", dim=True) + str(len(escrow_rows)))
    if check:
        click.echo(
            stylize(
                "READY: escrow config is present. The reveal watcher will use the same Lean verifier path.",
                fg="green",
            ),
        )
        return
    if once:
        click.echo(stylize("No revealed-claim transport is configured in this local slice.", fg="yellow"))
        click.echo(
            stylize(
                "Next implementation step: poll contract Reveal events and call `attestProof` after Lean PASS.",
                dim=True,
            ),
        )
        return
    click.echo(stylize("Use --check for preflight or --once for a single watcher pass.", dim=True))


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


def _bounty_status_color(status: str) -> str:
    return "green" if status == "open" else "yellow" if status in {"draft", "pending"} else "red"


def _bounty_rows(registry, *, show_all: bool):
    return [b for b in registry.bounties if show_all or b.status == "open"]


def _print_bounty_list(*, show_all: bool, registry=None) -> None:
    registry = registry or _load_bounty_registry()
    rows = _bounty_rows(registry, show_all=show_all)
    click.echo(stylize("Legacy dry-run bounties", fg="cyan", bold=True))
    click.echo(stylize(f"registry_sha256={registry.sha256}", dim=True))
    if not rows:
        click.echo(stylize("No open bounties.", fg="yellow"))
        if not show_all:
            click.echo(stylize("Try `lemma bounty list --all` to include closed and draft bounties.", dim=True))
        return
    for bounty in rows:
        reward = f"  {stylize('reward=', dim=True)}{bounty.reward}" if bounty.reward else ""
        deadline = f"  {stylize('deadline=', dim=True)}{bounty.deadline}" if bounty.deadline else ""
        click.echo(
            f"{stylize(bounty.id, fg='green', bold=True)}\t"
            f"{stylize(bounty.status, fg=_bounty_status_color(bounty.status))}\t"
            f"{bounty.title}{reward}{deadline}",
        )
    click.echo("")
    click.echo(
        stylize("Show details: ", dim=True)
        + stylize(f"lemma bounty show {rows[0].id}", fg="green")
        + stylize("  (or replace the id)", dim=True),
    )


def _print_bounty_detail(registry, bounty) -> None:
    source_name = bounty.source.get("name") or bounty.source.get("project") or "unknown"
    source_url = bounty.source.get("url")
    click.echo(stylize(bounty.title, fg="cyan", bold=True))
    click.echo(
        stylize("id=", dim=True)
        + stylize(bounty.id, fg="green", bold=True)
        + stylize("  status=", dim=True)
        + stylize(bounty.status, fg=_bounty_status_color(bounty.status))
        + stylize("  registry_sha256=", dim=True)
        + registry.sha256,
    )
    if bounty.reward:
        click.echo(stylize("reward: ", fg="yellow", bold=True) + bounty.reward)
    if bounty.deadline:
        click.echo(stylize("deadline: ", fg="yellow", bold=True) + bounty.deadline)
    if bounty.terms_url:
        click.echo(stylize("terms: ", dim=True) + bounty.terms_url)
    click.echo(stylize("source: ", dim=True) + source_name + (f" ({source_url})" if source_url else ""))
    click.echo("")
    click.echo(stylize("Lean target", fg="cyan", bold=True))
    click.echo(stylize("  theorem_id:   ", dim=True) + bounty.problem.id)
    click.echo(stylize("  theorem_name: ", dim=True) + stylize(bounty.problem.theorem_name, fg="green"))
    click.echo(stylize("  split:        ", dim=True) + stylize(bounty.problem.split, fg="yellow", bold=True))
    click.echo(stylize("  target_sha256: ", dim=True) + bounty.target_sha256)
    click.echo(stylize("  policy:       ", dim=True) + bounty.submission_policy)
    click.echo("")
    click.echo(stylize("Next", fg="cyan", bold=True))
    click.echo("  " + stylize(f"lemma mine {bounty.id} --submission Submission.lean", fg="green"))


def _show_bounty_or_hint(bounty_id: str | None) -> None:
    from lemma.bounty.client import BountyError

    registry = _load_bounty_registry()
    if bounty_id:
        try:
            bounty = registry.get(bounty_id)
        except BountyError as e:
            click.echo(stylize(str(e), fg="red", bold=True), err=True)
            click.echo("")
            _print_bounty_list(show_all=True, registry=registry)
            raise SystemExit(2) from e
        _print_bounty_detail(registry, bounty)
        return

    rows = _bounty_rows(registry, show_all=False)
    if len(rows) == 1:
        _print_bounty_detail(registry, rows[0])
        return
    _print_bounty_list(show_all=False, registry=registry)


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


@main.group(
    "bounty",
    hidden=True,
    invoke_without_command=True,
    help="Browse, verify, package, and submit bounty proofs.",
)
@click.option("--show", "show_hint", is_flag=True, help="Show the only open bounty, or list bounty IDs.")
@click.pass_context
def bounty_group(ctx: click.Context, show_hint: bool) -> None:
    if ctx.invoked_subcommand is None:
        if show_hint:
            _show_bounty_or_hint(None)
            return
        _print_bounty_list(show_all=False)


@bounty_group.command("list")
@click.option("--all", "show_all", is_flag=True, help="Show closed and draft bounties too.")
def bounty_list_cmd(show_all: bool) -> None:
    """List bounties from the remote registry."""
    _print_bounty_list(show_all=show_all)


@bounty_group.command("show")
@click.argument("bounty_id", required=False)
def bounty_show_cmd(bounty_id: str | None) -> None:
    """Show one bounty target and terms."""
    _show_bounty_or_hint(bounty_id)


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
    if settings.bounty_reward_custody != "local_dry_run":
        raise click.ClickException(
            "Legacy bounty packages are dry-run only. Use `lemma mine` for escrow-backed claims.",
        )
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
