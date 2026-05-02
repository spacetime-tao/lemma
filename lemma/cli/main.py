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


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Lemma subnet — Lean proofs + reasoning traces."""


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
        click.echo(f"netuid={settings.netuid} port={settings.axon_port}")
        return
    MinerService(settings).run()


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


@problems_grp.command("show")
@click.argument("problem_id")
def problems_show(problem_id: str) -> None:
    settings = LemmaSettings()
    p = resolve_problem(settings, problem_id)
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
