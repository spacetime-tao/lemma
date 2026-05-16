"""Miner forward handler for manually stored proofs."""

from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.subtensor import get_subtensor
from lemma.common.synapse_limits import synapse_payload_error
from lemma.lifecycle import target_phase
from lemma.miner.limits import reject_synopsis
from lemma.problems.factory import resolve_problem
from lemma.protocol import LemmaChallenge
from lemma.submissions import pending_submission_for_problem


def _with_computed_body_hash(synapse: LemmaChallenge) -> LemmaChallenge:
    return synapse.model_copy(update={"computed_body_hash": synapse.body_hash})


def _without_proof(synapse: LemmaChallenge) -> LemmaChallenge:
    synapse.proof_script = None
    synapse.proof_nonce = None
    synapse.commitment_hash = None
    return _with_computed_body_hash(synapse)


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

        try:
            current_block = int(get_subtensor(settings).get_current_block())
            phase = target_phase(settings, [], current_block)
        except Exception as exc:  # noqa: BLE001
            logger.warning("miner poll target_id={} proof=none phase_error={}", problem.id, exc)
            return _without_proof(synapse)
        if phase.name != "reveal":
            logger.info(
                "miner poll target_id={} proof=none phase={} reveal_block={} current_block={}",
                problem.id,
                phase.name,
                phase.reveal_block,
                phase.current_block,
            )
            return _without_proof(synapse)

        pending = pending_submission_for_problem(settings.miner_submissions_path, problem)
        if pending is None:
            logger.info("miner poll target_id={} proof=none", problem.id)
            return _without_proof(synapse)
        if pending.commitment_status != "committed" or not pending.proof_nonce or not pending.commitment_hash:
            logger.info(
                "miner poll target_id={} proof=none commitment_status={}",
                problem.id,
                pending.commitment_status,
            )
            return _without_proof(synapse)

        synapse.proof_script = pending.proof_script
        synapse.proof_nonce = pending.proof_nonce
        synapse.commitment_hash = pending.commitment_hash
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
