"""Lemma CLI."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from lemma import __version__
from lemma.cli.style import colors_enabled, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import get_problem_source, resolve_problem


def _resolve_problem_or_click(settings: LemmaSettings, problem_id: str):
    try:
        return resolve_problem(settings, problem_id)
    except KeyError as exc:
        raise click.ClickException(f"unknown target id: {problem_id}") from exc


@click.group(name="lemma", invoke_without_command=True, context_settings={"max_content_width": 100})
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Winner-take-all manual Lean proof formalization."""
    if ctx.invoked_subcommand is not None:
        return
    click.echo(stylize("Lemma ", fg="cyan", bold=True) + stylize(__version__, dim=True))
    click.echo("Manual proof submission. First valid Lean proof wins.\n")
    click.echo(ctx.get_help(), color=colors_enabled())


@main.group("target", invoke_without_command=True)
@click.pass_context
def target_group(ctx: click.Context) -> None:
    """Show the active target and solved ledger."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(target_show_cmd, target_id=None)


@target_group.command("show")
@click.argument("target_id", required=False)
def target_show_cmd(target_id: str | None) -> None:
    from lemma.cli.problem_views import echo_challenge_separator, echo_problem_card
    from lemma.problems.known_theorems import known_theorems_manifest_sha256
    from lemma.wta import current_champion

    settings = LemmaSettings()
    src = get_problem_source(settings)
    try:
        problem = src.get(target_id.strip()) if target_id else src.sample(seed=0)
    except KeyError as exc:
        raise click.ClickException(f"unknown target id: {target_id}") from exc
    champion = current_champion(settings.wta_ledger_path)
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    click.echo(stylize("Lemma target", fg="cyan", bold=True))
    click.echo(stylize(f"manifest_sha256={manifest_sha}", dim=True))
    champion_text = (
        "champion=<none yet>"
        if champion is None
        else f"champion_uid={champion.winner_uid} last_solved={champion.target_id}"
    )
    click.echo(stylize(champion_text, fg="yellow"))
    click.echo("")
    echo_problem_card(problem, heading="Active theorem" if target_id is None else "Theorem")
    ref = problem.extra.get("human_proof_reference")
    if isinstance(ref, dict):
        click.echo(stylize("proof_reference=" + str(ref.get("citation") or ""), dim=True))
    review = problem.extra.get("review")
    if isinstance(review, dict):
        click.echo(stylize("duplicate_check=" + str(review.get("duplicate_check") or ""), dim=True))
    echo_challenge_separator()
    click.echo(problem.challenge_source())


@target_group.command("ledger")
def target_ledger_cmd() -> None:
    from lemma.wta import load_wta_ledger, resolved_wta_ledger_path

    settings = LemmaSettings()
    path = resolved_wta_ledger_path(settings.wta_ledger_path)
    entries = load_wta_ledger(settings.wta_ledger_path)
    click.echo(stylize("Lemma ledger", fg="cyan", bold=True))
    click.echo(stylize(str(path), dim=True))
    if not entries:
        click.echo("No solved targets yet.")
        return
    for entry in entries:
        click.echo(
            f"{entry.target_id}\twinner_uid={entry.winner_uid}\tproof={entry.proof_sha256[:16]}\t"
            f"block={entry.accepted_block}",
        )


@main.command("submit")
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--verify/--no-verify", "do_verify", default=True, help="Verify before storing the proof.")
@click.option("--host-lean", is_flag=True, help="With --verify, use host lake. Requires LEMMA_ALLOW_HOST_LEAN=1.")
def submit_cmd(problem_id: str, submission_path: Path, do_verify: bool, host_lean: bool) -> None:
    from lemma.lean.verify_runner import run_lean_verify
    from lemma.submissions import resolved_submissions_path, save_pending_submission

    settings = LemmaSettings()
    problem = _resolve_problem_or_click(settings, problem_id)
    proof_script = submission_path.read_text(encoding="utf-8")
    verify_reason = "not_run"
    build_seconds = 0.0
    if do_verify:
        if host_lean and not settings.allow_host_lean:
            raise click.ClickException("Host Lean is disabled. Set LEMMA_ALLOW_HOST_LEAN=1 or omit --host-lean.")
        eff = settings.model_copy(update={"lean_use_docker": not host_lean and settings.lean_use_docker})
        vr = run_lean_verify(
            eff,
            verify_timeout_s=settings.lean_verify_timeout_s,
            problem=problem,
            proof_script=proof_script,
        )
        if not vr.passed:
            raise click.ClickException(f"Lean verify failed: {vr.reason}\n{vr.stderr_tail}")
        verify_reason = vr.reason
        build_seconds = float(vr.build_seconds)
    entry = save_pending_submission(settings.miner_submissions_path, problem, proof_script)
    heading = "Valid proof stored" if do_verify else "Proof stored without validity confirmation"
    click.echo(stylize(heading, fg="green" if do_verify else "yellow", bold=True))
    click.echo(f"target_id={entry.target_id}")
    click.echo(f"verified={str(do_verify).lower()}")
    click.echo(f"verify_reason={verify_reason}")
    click.echo(f"build_seconds={build_seconds:.2f}")
    click.echo(f"proof_sha256={entry.proof_sha256}")
    click.echo(f"store={resolved_submissions_path(settings.miner_submissions_path)}")
    click.echo(f"ready_to_serve={str(do_verify).lower()}")


@main.group("miner", invoke_without_command=True, help="Serve manually submitted proofs to validators.")
@click.pass_context
def miner_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@miner_group.command("start")
def miner_start_cmd() -> None:
    from lemma.miner.service import MinerService

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    MinerService(settings).run()


@main.group("validator", invoke_without_command=True, help="Poll miners, Lean verify, and set champion weights.")
@click.pass_context
def validator_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@validator_group.command("start")
def validator_start_cmd() -> None:
    from lemma.validator.service import ValidatorService

    ValidatorService(LemmaSettings(), dry_run=False).run_blocking()


@validator_group.command("dry-run")
def validator_dry_run_cmd() -> None:
    from lemma.validator.service import ValidatorService

    ValidatorService(LemmaSettings(), dry_run=True).run_blocking()


@validator_group.command("check")
def validator_check_cmd() -> None:
    from lemma.cli.validator_check import run_validator_check

    raise SystemExit(run_validator_check(LemmaSettings()))


@main.command("verify")
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--host-lean", is_flag=True, help="Run lake on host. Requires LEMMA_ALLOW_HOST_LEAN=1.")
def verify_cmd(problem_id: str, submission_path: Path, host_lean: bool) -> None:
    from lemma.lean.verify_runner import run_lean_verify

    settings = LemmaSettings()
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException("Host Lean is disabled. Set LEMMA_ALLOW_HOST_LEAN=1 or omit --host-lean.")
    proof_script = submission_path.read_text(encoding="utf-8")
    problem = _resolve_problem_or_click(settings, problem_id)
    eff = settings.model_copy(update={"lean_use_docker": not host_lean and settings.lean_use_docker})
    vr = run_lean_verify(
        eff,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=problem,
        proof_script=proof_script,
    )
    click.echo(vr.model_dump_json(indent=2))
    sys.exit(0 if vr.passed else 1)


@main.command("meta")
@click.option("--raw", is_flag=True)
def meta_cmd(raw: bool) -> None:
    import json

    from lemma.problems.known_theorems import known_theorems_manifest, known_theorems_manifest_sha256
    from lemma.validator.profile import validator_profile_dict, validator_profile_sha256

    settings = LemmaSettings()
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    profile = validator_profile_dict(settings)
    profile_sha = validator_profile_sha256(settings)
    if raw:
        click.echo(f"lemma_version={__version__}")
        click.echo("problem_source=known_theorems")
        click.echo(f"known_theorems_manifest_sha256={manifest_sha}")
        click.echo(
            "known_theorems_manifest_json="
            + json.dumps(known_theorems_manifest(settings.known_theorems_manifest_path), sort_keys=True),
        )
        click.echo(f"validator_profile_sha256={profile_sha}")
        click.echo("validator_profile_json=" + json.dumps(profile, sort_keys=True))
        return
    click.echo(stylize("Lemma fingerprints", fg="cyan", bold=True))
    click.echo(f"known_theorems_manifest_sha256={manifest_sha}")
    click.echo(f"validator_profile_sha256={profile_sha}")
