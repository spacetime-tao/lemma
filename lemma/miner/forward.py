"""Axon forward handler."""

import asyncio

from lemma.common.config import LemmaSettings
from lemma.miner.daily_budget import allow_daily_forward
from lemma.miner.limits import reject_synopsis, synapse_payload_error
from lemma.miner.model_card import prover_model_card_text
from lemma.miner.prover import Prover
from lemma.protocol import LemmaChallenge


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
