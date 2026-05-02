"""Run the prover once against the same theorem validators would sample at current head."""

from __future__ import annotations

import asyncio
import os
import time

import click

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.problem_seed import resolve_problem_seed
from lemma.common.subtensor import get_subtensor
from lemma.lean.sandbox import LeanSandbox
from lemma.miner.prover import LLMProver
from lemma.problems.factory import get_problem_source
from lemma.protocol import LemmaChallenge
from lemma.reasoning.format import format_reasoning_steps


def run_try_prover(settings: LemmaSettings, *, verify: bool, block: int | None) -> None:
    """Load current (or --block) seed, call LLM prover, print trace + proof; optional Lean verify."""
    setup_logging(settings.log_level)
    from lemma import __version__

    try:
        subtensor = get_subtensor(settings)
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(
            f"Chain RPC required (same as `lemma status`): {e}",
        ) from e

    try:
        head = int(block) if block is not None else int(subtensor.get_current_block())
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(str(e)) from e

    problem_seed, seed_tag = resolve_problem_seed(
        chain_head_block=head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )
    src = get_problem_source(settings)
    problem = src.sample(seed=problem_seed)
    timeout_s = float(settings.dendrite_timeout_s)
    synapse = LemmaChallenge(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        deadline_unix=int(time.time()) + int(timeout_s),
        metronome_id=str(problem_seed),
        timeout=timeout_s,
    )

    click.echo(stylize(f"lemma {__version__} — try-prover", fg="cyan", bold=True))
    click.echo(
        stylize(f"chain_head_block={head} problem_seed={problem_seed} ({seed_tag})", dim=True),
    )
    click.echo(stylize(f"theorem_id={problem.id}  {problem.theorem_name}", fg="green"))
    click.echo(
        stylize(
            "Calling your prover LLM (no axon / no other miners). This can take minutes.",
            dim=True,
        ),
    )
    click.echo("")

    prover = LLMProver(settings)

    async def _solve() -> None:
        trace, proof, steps = await prover.solve(synapse)

        click.echo(stylize("— Reasoning (informal) —", fg="cyan", bold=True))
        if steps:
            click.echo(format_reasoning_steps(steps))
        else:
            click.echo(trace or "(empty)")
        click.echo("")
        click.echo(stylize("— proof_script (Submission.lean) —", fg="cyan", bold=True))
        click.echo(proof or "(empty)")
        click.echo("")

        etext = format_reasoning_steps(steps) if steps else (trace or "")
        click.echo(stylize(f"(effective reasoning chars for judge: {len(etext)})", dim=True))

        if verify and (proof or "").strip():
            sandbox = LeanSandbox(
                image=settings.lean_sandbox_image,
                cpu=settings.lean_sandbox_cpu,
                mem_mb=settings.lean_sandbox_mem_mb,
                timeout_s=settings.lean_verify_timeout_s,
                network_mode=settings.lean_sandbox_network,
                use_docker=os.environ.get("LEMMA_USE_DOCKER", "1") != "0",
            )
            click.echo("")
            click.echo(stylize("— Local Lean verify —", fg="cyan", bold=True))
            vr = await asyncio.to_thread(sandbox.verify, problem, proof)
            if vr.passed:
                click.echo(stylize("PASS", fg="green") + f"  ({vr.build_seconds:.2f}s)")
            else:
                click.echo(stylize(f"FAIL  {vr.reason}", fg="red", bold=True))
                if vr.stderr_tail:
                    click.echo(vr.stderr_tail[-8000:])

    asyncio.run(_solve())
