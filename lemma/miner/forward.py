"""Axon forward handler."""

from __future__ import annotations

import asyncio
import os

from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.lean.sandbox import LeanSandbox
from lemma.miner.daily_budget import allow_daily_forward
from lemma.miner.limits import reject_synopsis, synapse_payload_error
from lemma.miner.model_card import prover_model_card_text
from lemma.miner.prover import Prover
from lemma.problems.factory import resolve_problem
from lemma.protocol import LemmaChallenge


def _excerpt(text: str, max_chars: int = 12_000) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n... [truncated] ...\n" + text[-half:]


def make_forward(settings: LemmaSettings, prover: Prover):
    sem = asyncio.Semaphore(max(1, settings.miner_max_concurrent_forwards))

    async def forward(synapse: LemmaChallenge) -> LemmaChallenge:
        err = synapse_payload_error(synapse, settings)
        if err:
            return reject_synopsis(synapse, 413, err)

        if settings.miner_max_forwards_per_day > 0 and not allow_daily_forward(settings.miner_max_forwards_per_day):
            return reject_synopsis(
                synapse,
                429,
                f"daily forward limit reached ({settings.miner_max_forwards_per_day}/UTC day)",
            )

        async with sem:
            trace, proof, steps = await prover.solve(synapse)

        if settings.miner_log_forwards:
            logger.info(
                "miner forward theorem_id={} trace_chars={} proof_chars={}",
                synapse.theorem_id,
                len(trace or ""),
                len(proof or ""),
            )
            logger.info("reasoning (excerpt):\n{}", _excerpt(trace or ""))
            logger.info("proof_script (excerpt):\n{}", _excerpt(proof or ""))

        if settings.miner_local_verify and (proof or "").strip():
            try:
                problem = resolve_problem(settings, synapse.theorem_id)
            except Exception as e:  # noqa: BLE001
                logger.warning("miner local verify skipped (could not load problem): {}", e)
            else:
                sandbox = LeanSandbox(
                    image=settings.lean_sandbox_image,
                    cpu=settings.lean_sandbox_cpu,
                    mem_mb=settings.lean_sandbox_mem_mb,
                    timeout_s=settings.lean_verify_timeout_s,
                    network_mode=settings.lean_sandbox_network,
                    use_docker=os.environ.get("LEMMA_USE_DOCKER", "1") != "0",
                )
                vr = await asyncio.to_thread(sandbox.verify, problem, proof)
                if vr.passed:
                    logger.info(
                        "miner local verify OK theorem_id={} build_s={:.2f}",
                        synapse.theorem_id,
                        vr.build_seconds,
                    )
                else:
                    logger.warning(
                        "miner local verify FAIL theorem_id={} reason={} build_s={:.2f}",
                        synapse.theorem_id,
                        vr.reason,
                        vr.build_seconds,
                    )
                    logger.warning("stderr_tail:\n{}", _excerpt(vr.stderr_tail or "", 8000))

        synapse.reasoning_steps = steps
        synapse.reasoning_trace = trace
        synapse.proof_script = proof
        synapse.model_card = prover_model_card_text(settings)

        err = synapse_payload_error(synapse, settings)
        if err:
            return reject_synopsis(synapse, 413, err)
        return synapse

    return forward


def priority_stub(synapse: LemmaChallenge) -> float:
    return 0.0
