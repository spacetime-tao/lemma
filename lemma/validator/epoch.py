"""One scoring round: broadcast, verify, judge, Pareto, set_weights."""

from __future__ import annotations

import asyncio
import os
import time
from typing import TYPE_CHECKING, Any

import bittensor as bt
from loguru import logger

from lemma.common.subtensor import get_subtensor
from lemma.common.uids import axon_list_for_uids
from lemma.judge.anthropic_judge import AnthropicJudge
from lemma.judge.base import Judge
from lemma.judge.fake import FakeJudge
from lemma.judge.fingerprint import rubric_sha256
from lemma.judge.openai_judge import OpenAIJudge
from lemma.lean.sandbox import LeanSandbox, VerifyResult
from lemma.problems.base import ProblemSource
from lemma.protocol import LemmaChallenge
from lemma.reasoning.format import effective_reasoning_text
from lemma.scoring.pareto import ScoredEntry, pareto_weights
from lemma.scoring.rewards import entry_from_scores
from lemma.validator import query as q
from lemma.validator.training_export import append_epoch_jsonl, training_record
from lemma.validator.weights_policy import build_full_weights

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def _build_judge(settings: LemmaSettings, dry_run: bool) -> Judge:
    if dry_run or os.environ.get("LEMMA_FAKE_JUDGE") == "1":
        return FakeJudge()
    prov = (settings.judge_provider or "openai").lower()
    if prov == "openai":
        key = settings.openai_api_key
        if not key:
            logger.warning("OPENAI_API_KEY missing; using FakeJudge")
            return FakeJudge()
        return OpenAIJudge(
            key,
            settings.openai_model,
            base_url=settings.openai_base_url,
            temperature=settings.judge_temperature,
            max_tokens=settings.judge_max_tokens,
        )
    key = settings.anthropic_api_key
    if not key:
        logger.warning("ANTHROPIC_API_KEY missing; using FakeJudge")
        return FakeJudge()
    return AnthropicJudge(
        key,
        settings.anthropic_model,
        temperature=settings.judge_temperature,
        max_tokens=settings.judge_max_tokens,
    )


async def run_epoch(
    settings: LemmaSettings,
    problem_source: ProblemSource,
    dry_run: bool = False,
    dendrite_timeout: float | None = None,
) -> dict[int, float]:
    t_epoch = time.perf_counter()
    wallet = bt.Wallet(name=settings.wallet_cold, hotkey=settings.wallet_hot)
    subtensor = get_subtensor(settings)
    netuid = settings.netuid
    cur_block = subtensor.get_current_block()
    metagraph = subtensor.metagraph(netuid)
    raw_n = metagraph.n
    n = int(raw_n.item()) if hasattr(raw_n, "item") else int(raw_n)

    my_uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid)
    if settings.validator_abort_if_not_registered and my_uid is None:
        logger.warning("Validator wallet has no UID on subnet {}; skipping epoch", netuid)
        return {}

    timeout = float(dendrite_timeout if dendrite_timeout is not None else settings.dendrite_timeout_s)

    uids = [u for u in range(n) if my_uid is None or u != my_uid]
    if not uids:
        logger.warning("No peer UIDs to query")
        return {}

    logger.debug("canonical judge rubric sha256={}", rubric_sha256())

    problem = problem_source.sample(seed=cur_block)
    synapse = LemmaChallenge(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        deadline_unix=int(time.time()) + int(timeout),
        metronome_id=str(cur_block),
        timeout=timeout,
    )

    dendrite = bt.Dendrite(wallet=wallet)
    axons = axon_list_for_uids(metagraph, uids)
    responses = await q.query_miners(dendrite, axons, synapse, timeout=timeout)

    sandbox = LeanSandbox(
        image=settings.lean_sandbox_image,
        cpu=settings.lean_sandbox_cpu,
        mem_mb=settings.lean_sandbox_mem_mb,
        timeout_s=settings.lean_verify_timeout_s,
        network_mode=settings.lean_sandbox_network,
        use_docker=os.environ.get("LEMMA_USE_DOCKER", "1") != "0",
    )
    judge = _build_judge(settings, dry_run)

    verified: list[tuple[int, LemmaChallenge, VerifyResult]] = []
    judge_errors = 0
    export_path = settings.training_export_jsonl
    training_rows: list[dict[str, Any]] = []
    for uid, resp in zip(uids, responses, strict=True):
        if not isinstance(resp, LemmaChallenge):
            continue
        if not resp.is_success:
            continue
        if not resp.proof_script:
            continue
        vr = sandbox.verify(problem, resp.proof_script)
        if vr.passed:
            verified.append((uid, resp, vr))
        else:
            logger.debug("uid={} verify failed: {}", uid, vr.reason)

    async def _score_one(item: tuple[int, LemmaChallenge, VerifyResult]) -> ScoredEntry | None:
        nonlocal judge_errors
        uid, resp, _vr = item
        trace_text = effective_reasoning_text(resp)
        try:
            rubric = await judge.score(
                resp.theorem_statement,
                trace_text,
                resp.proof_script or "",
            )
        except Exception as e:  # noqa: BLE001
            judge_errors += 1
            logger.warning("judge failed uid={} err={}", uid, e)
            return None
        if export_path:
            training_rows.append(
                training_record(
                    block=cur_block,
                    theorem_id=problem.id,
                    uid=uid,
                    resp=resp,
                    rubric=rubric,
                )
            )
        return entry_from_scores(uid, rubric, trace_text)

    scored = [x for x in await asyncio.gather(*[_score_one(v) for v in verified]) if x is not None]
    weights_by_uid = pareto_weights(scored)

    if export_path and training_rows:
        append_epoch_jsonl(export_path, training_rows, weights_by_uid)
        logger.debug(
            "training_export appended {} rows to {}",
            len(training_rows),
            export_path,
        )

    full_weights, skip_chain_write = build_full_weights(
        n,
        weights_by_uid,
        empty_policy=settings.empty_epoch_weights_policy,
    )

    elapsed = time.perf_counter() - t_epoch
    logger.info(
        "lemma_epoch_summary block={} theorem_id={} verified={} scored={} pareto_entries={} "
        "judge_errors={} skip_set_weights={} seconds={:.2f}",
        cur_block,
        problem.id,
        len(verified),
        len(scored),
        len(weights_by_uid),
        judge_errors,
        skip_chain_write,
        elapsed,
    )

    if dry_run:
        logger.info("DRY RUN weights (subset): {}", weights_by_uid)
        return weights_by_uid

    if skip_chain_write:
        logger.warning(
            "Skipping set_weights (empty scores policy={})",
            settings.empty_epoch_weights_policy,
        )
        return weights_by_uid

    delay = settings.set_weights_retry_delay_s
    last_out = None
    for attempt in range(settings.set_weights_max_retries):
        last_out = subtensor.set_weights(
            wallet=wallet,
            netuid=netuid,
            uids=list(range(n)),
            weights=full_weights,
            wait_for_inclusion=False,
            wait_for_finalization=False,
        )
        ok = getattr(last_out, "success", True)
        if ok:
            break
        logger.warning("set_weights attempt {} failed; retrying", attempt + 1)
        await asyncio.sleep(delay * (2**attempt))

    logger.info(
        "set_weights success={} message={}",
        getattr(last_out, "success", last_out),
        getattr(last_out, "message", ""),
    )
    return weights_by_uid
