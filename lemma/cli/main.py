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


@click.group(invoke_without_command=True, context_settings={"max_content_width": 100})
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Lemma subnet — Lean proofs (Bittensor).

    \b
    Common commands:
      lemma-cli rehearsal  Live theorem → prover → Lean preview
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
            + stylize(" — prover + Lean on the live theorem (costs APIs)", dim=True),
        )
        click.echo(stylize("  Docs: docs/getting-started.md · docs/miner.md · docs/validator.md\n", dim=True))
        return


@main.command("meta")
@click.option(
    "--raw",
    is_flag=True,
    help="Compact key=value lines (original layout; best for scripts and copy-paste diffs).",
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
        click.echo(f"judge_profile_sha256={prof_sha}")
        click.echo("judge_profile_json=" + json.dumps(prof, sort_keys=True))
        return

    click.echo(stylize("Subnet fingerprints", fg="cyan", bold=True))
    click.echo(
        stylize("Prints canonical hashes only; it does not edit `.env`.\n", dim=True)
        + stylize("  lemma-cli configure subnet-pins\n", fg="green", bold=True)
        + stylize("  or copy values from ", dim=True)
        + stylize("lemma meta --raw", fg="green")
        + stylize(".\n", dim=True),
        nl=False,
    )
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
            "session totals; LEMMA_MINER_LOG_FORWARDS=1 includes proof excerpts; "
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
        + stylize("lemma-cli miner-observability", fg="green")
        + stylize(" — what you can see in this terminal · ", dim=True)
        + stylize("lemma-cli", fg="green")
        + stylize(" — friendly operator screen.\n", dim=True),
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
    help="Explain how to see forwards in logs vs on-chain incentives (proof scores are not returned to the axon).",
)
def miner_observability_cmd() -> None:
    _echo_moved_to_lemma_cli(("miner-observability",), heading="Miner observability moved to lemma-cli.")


MOVED_COMMAND_CONTEXT = {
    "ignore_unknown_options": True,
    "allow_extra_args": True,
}
MOVED_MAIN_COMMANDS = (
    ("start", "Guided setup moved to lemma-cli."),
    ("doctor", "Doctor moved to lemma-cli."),
    ("docs", "Docs helper moved to lemma-cli."),
    ("status", "Status view moved to lemma-cli."),
    ("problems", "Problem inspector moved to lemma-cli."),
    ("judge", "Judge preview moved to lemma-cli."),
    ("try-prover", "Try-prover moved to lemma-cli."),
    ("rehearsal", "Rehearsal moved to lemma-cli."),
    ("setup", "Interactive setup moved to lemma-cli."),
    ("glossary", "Glossary moved to lemma-cli."),
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


def _register_moved_main_command(command: str, heading: str) -> None:
    @main.command(command, context_settings=MOVED_COMMAND_CONTEXT, add_help_option=False, help=heading)
    @click.argument("args", nargs=-1, type=click.UNPROCESSED)
    def moved_main_command(args: tuple[str, ...], command: str = command, heading: str = heading) -> None:
        _echo_moved_to_lemma_cli((command, *args), heading=heading)


for _moved_command, _moved_heading in MOVED_MAIN_COMMANDS:
    _register_moved_main_command(_moved_command, _moved_heading)


@main.command(
    "configure",
    context_settings=MOVED_COMMAND_CONTEXT,
    add_help_option=False,
    help="Interactive `.env` prompts moved to lemma-cli.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def configure_cmd(args: tuple[str, ...]) -> None:
    _echo_moved_to_lemma_cli(("configure", *args))


def _validator_run_blocking(*, dry_run: bool) -> None:
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    ValidatorService(settings, dry_run=dry_run).run_blocking()


@main.group(
    "validator",
    invoke_without_command=True,
    help=(
        "Validator — query miners, Lean verify, proof-score, optional set_weights. "
        "Local scoring preview (no metagraph): lemma-cli rehearsal. "
        "Judge-only on files: lemma-cli judge --trace FILE. "
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
        "Use `lemma validator start`, `lemma validator dry-run`, "
        "or `lemma validator-check`."
    )
    click.echo("For the friendly operator screen, use `lemma-cli`.")


@validator_group.command("start", help="Run scoring rounds until Ctrl+C.")
def validator_start_cmd() -> None:
    _validator_run_blocking(dry_run=False)


@validator_group.command(
    "dry-run",
    help=(
        "Full proof-only scoring epochs without set_weights (chain + miners + Lean). "
        "Judge-only smoke test: lemma-cli judge --trace FILE."
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


@validator_group.command(
    "config",
    context_settings=MOVED_COMMAND_CONTEXT,
    add_help_option=False,
    help="Validator config summary moved to lemma-cli.",
)
@click.argument("args", nargs=-1, type=click.UNPROCESSED)
def validator_config_cmd(args: tuple[str, ...]) -> None:
    _echo_moved_to_lemma_cli(("validator-config", *args), heading="Validator config moved to lemma-cli.")


@main.command(
    "validator-check",
    help="Pre-flight: chain, wallet UID, profile pins, Lean image (before `lemma validator start`).",
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
