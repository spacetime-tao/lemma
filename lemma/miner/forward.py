"""Miner forward handler for manual WTA proofs."""

from __future__ import annotations

from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.synapse_limits import synapse_payload_error
from lemma.miner.limits import reject_synopsis
from lemma.problems.factory import resolve_problem
from lemma.protocol import LemmaChallenge
from lemma.submissions import pending_submission_for_problem


def _with_computed_body_hash(synapse: LemmaChallenge) -> LemmaChallenge:
    return synapse.model_copy(update={"computed_body_hash": synapse.body_hash})


def make_forward(settings: LemmaSettings):
    async def forward(synapse: LemmaChallenge) -> LemmaChallenge:
        err = synapse_payload_error(synapse, settings, response=False)
        if err:
            return reject_synopsis(synapse, 413, err)

        try:
            problem = resolve_problem(settings, synapse.theorem_id)
        except Exception:
            return reject_synopsis(synapse, 404, f"unknown target: {synapse.theorem_id}")

        if synapse.theorem_statement != problem.challenge_source():
            return reject_synopsis(synapse, 400, "target statement mismatch")
        if list(synapse.imports or []) != list(problem.imports):
            return reject_synopsis(synapse, 400, "target imports mismatch")
        if synapse.lean_toolchain != problem.lean_toolchain or synapse.mathlib_rev != problem.mathlib_rev:
            return reject_synopsis(synapse, 400, "target toolchain mismatch")

        pending = pending_submission_for_problem(settings.miner_submissions_path, problem)
        if pending is None:
            logger.info("miner poll target_id={} proof=none", problem.id)
            synapse.proof_script = None
            return _with_computed_body_hash(synapse)

        synapse.proof_script = pending.proof_script
        err = synapse_payload_error(synapse, settings)
        if err:
            return reject_synopsis(synapse, 413, err)
        logger.info(
            "miner poll target_id={} proof_sha256={} proof_chars={}",
            problem.id,
            pending.proof_sha256,
            len(pending.proof_script),
        )
        return _with_computed_body_hash(synapse)

    return forward
