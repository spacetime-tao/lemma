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
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.factory import get_problem_source, resolve_problem


@click.group(invoke_without_command=True)
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Lemma subnet — Lean proofs + reasoning traces.

    Run with no subcommand to open the START HERE menu (`lemma start`).
    """
    if ctx.invoked_subcommand is None:
        from lemma.cli.start_screen import show_start_here

        show_start_here(ctx, group=main)


@main.command("start")
@click.pass_context
def start_cmd(ctx: click.Context) -> None:
    """STEP-BY-STEP onboarding (same as running `lemma` with no arguments)."""
    from lemma.cli.start_screen import show_start_here

    show_start_here(ctx, group=main)


@main.command("doctor")
def doctor_cmd() -> None:
    """Quick checks: venv, config load, optional chain RPC."""
    ok = True
    root = Path.cwd()
    if (root / ".venv").is_dir():
        click.echo("OK .venv present (uv sync --extra dev)")
    else:
        click.echo("MISSING .venv — run: uv sync --extra dev", err=True)
        ok = False
    try:
        s = LemmaSettings()
        click.echo(f"OK config NETUID={s.netuid} problem_source={s.problem_source}")
    except Exception as e:  # noqa: BLE001
        click.echo(f"CONFIG ERROR: {e}", err=True)
        raise SystemExit(1) from e
    try:
        from lemma.common.subtensor import get_subtensor

        head = int(get_subtensor(s).get_current_block())
        click.echo(f"OK chain RPC head_block={head}")
    except Exception as e:  # noqa: BLE001
        click.echo(f"SKIP chain RPC (offline OK): {e}")
    click.echo("")
    click.echo("START HERE: `lemma` or `lemma start`  ·  Doc paths: `lemma docs`")
    if not ok:
        raise SystemExit(1)
    click.echo("doctor: OK")


@main.command("docs")
def docs_cmd() -> None:
    """Print paths to main documentation files in this repository."""
    repo = Path(__file__).resolve().parents[2]
    click.echo("Open or preview these files:")
    for rel in (
        "docs/GETTING_STARTED.md",
        "docs/FAQ.md",
        "docs/MINER.md",
        "docs/VALIDATOR.md",
        "docs/MODELS.md",
        "docs/TESTING.md",
    ):
        path = repo / rel
        click.echo(f"  {path}" if path.is_file() else f"  {rel} (not found)")


@main.command("meta")
def meta_cmd() -> None:
    """Print canonical fingerprints (problem registry + judge rubric/profile for validator parity)."""
    import json

    from lemma.judge.fingerprint import rubric_sha256
    from lemma.judge.profile import judge_profile_dict, judge_profile_sha256
    from lemma.problems.generated import generated_registry_canonical_dict, generated_registry_sha256

    s = LemmaSettings()
    click.echo(f"lemma_version={__version__}")
    click.echo(f"problem_source={s.problem_source}")
    click.echo(f"generated_registry_sha256={generated_registry_sha256()}")
    click.echo("generated_registry_json=" + json.dumps(generated_registry_canonical_dict(), sort_keys=True))
    click.echo(f"judge_rubric_sha256={rubric_sha256()}")
    click.echo(f"judge_profile_sha256={judge_profile_sha256(s)}")
    click.echo("judge_profile_json=" + json.dumps(judge_profile_dict(s), sort_keys=True))


@main.command("status")
def status_cmd() -> None:
    """Chain head + theorem seed (same rule as validators in ``run_epoch``)."""
    from lemma.common.problem_seed import resolve_problem_seed
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

    problem_seed, seed_tag = resolve_problem_seed(
        chain_head_block=block,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )
    p = src.sample(seed=problem_seed)
    click.echo(f"problem_source={settings.problem_source}")
    click.echo(f"LEMMA_PROBLEM_SEED_MODE={settings.problem_seed_mode}")
    click.echo(f"LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS={settings.problem_seed_quantize_blocks}")
    click.echo(f"chain_head_block={block}")
    click.echo(f"problem_seed_tag={seed_tag}")
    click.echo(f"problem_seed={problem_seed}")
    click.echo(f"sampled_theorem_id={p.id}")
    click.echo(f"theorem_name={p.theorem_name}")
    click.echo(f"split_bucket={p.split}")
    extra = p.extra or {}
    if isinstance(extra, dict) and extra.get("template_fn"):
        click.echo(f"template_fn={extra.get('template_fn')}")
    click.echo("")
    click.echo("Print Challenge.lean:")
    click.echo("  lemma problems show --current")
    click.echo("")
    click.echo("Subnet fingerprints (align validators):")
    click.echo("  lemma meta")


@main.command("miner", help="Run the miner axon")
@click.option("--dry-run", is_flag=True, help="Log config only (does not start axon)")
@click.option(
    "--max-forwards-per-day",
    type=int,
    default=None,
    help="Cap prover forwards per UTC day (savings mode); 0=unlimited. Overrides MINER_MAX_FORWARDS_PER_DAY.",
)
def miner_cmd(dry_run: bool, max_forwards_per_day: int | None) -> None:
    """Run the miner axon."""
    from lemma.miner.service import MinerService

    if max_forwards_per_day is not None:
        os.environ["MINER_MAX_FORWARDS_PER_DAY"] = str(max_forwards_per_day)

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    if dry_run:
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
            click.echo(
                "axon_external_ip=<unset; set AXON_EXTERNAL_IP or enable AXON_DISCOVER_EXTERNAL_IP>"
            )
        return
    MinerService(settings).run()


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
        "Role",
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
    """Set LEAN_SANDBOX_IMAGE for validators."""
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


@main.command("validator")
@click.option("--dry-run", is_flag=True, default=None, help="Skip on-chain set_weights")
def validator_cmd(dry_run: bool | None) -> None:
    """Run the validator metronome loop."""
    from lemma.validator.service import ValidatorService

    settings = LemmaSettings()
    dr = dry_run if dry_run is not None else os.environ.get("LEMMA_DRY_RUN") == "1"
    ValidatorService(settings, dry_run=dr).run_blocking()


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


@main.group("problems")
def problems_grp() -> None:
    """Inspect catalog rows (frozen JSON) or explain generated mode."""


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

    Provide exactly one of: PROBLEM_ID, --current, or --block N.
    """
    from lemma.common.problem_seed import resolve_problem_seed

    settings = LemmaSettings()
    src = get_problem_source(settings)

    n_sel = sum([bool(problem_id and problem_id.strip()), current, block is not None])
    if n_sel != 1:
        raise click.UsageError("Specify exactly one of: PROBLEM_ID, --current (-c), or --block N.")

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
        click.echo(f"# chain_head_block={head} problem_seed={seed} tag={tag} theorem_id={p.id}\n")
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
        click.echo(f"# chain_head_block={head} problem_seed={seed} tag={tag} theorem_id={p.id}\n")
        click.echo(p.challenge_source())
        return

    assert problem_id is not None  # guaranteed by n_sel with current/block exhausted
    p = resolve_problem(settings, problem_id.strip())
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
