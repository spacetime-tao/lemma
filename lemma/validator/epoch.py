"""One scoring round: broadcast, verify, judge, Pareto, set_weights."""

from __future__ import annotations

import asyncio
import os
import time
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import bittensor as bt
from loguru import logger

from lemma.common.block_deadline import compute_forward_deadline_and_wait
from lemma.common.problem_seed import (
    effective_chain_head_for_problem_seed,
    mix_sub_problem_seed,
    resolve_problem_seed,
)
from lemma.common.split_timeout import split_timeout_multiplier
from lemma.common.subtensor import get_subtensor
from lemma.common.uids import axon_list_for_uids
from lemma.judge.anthropic_judge import AnthropicJudge
from lemma.judge.base import Judge
from lemma.judge.fake import FakeJudge
from lemma.judge.fingerprint import rubric_sha256
from lemma.judge.openai_judge import OpenAIJudge
from lemma.lean.sandbox import VerifyResult
from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem, ProblemSource
from lemma.protocol import LemmaChallenge, synapse_miner_response_integrity_ok
from lemma.protocol_attest import (
    attest_spot_should_full_verify,
    miner_verify_attest_message,
    verify_miner_verify_attest_signature,
)
from lemma.protocol_commit_reveal import (
    looks_like_commitment_hex,
    reasoning_blob_for_commit,
    verify_reveal_against_commitment,
)
from lemma.reasoning.format import effective_reasoning_text
from lemma.scoring.dedup import dedup_coldkeys, dedup_identical_submissions
from lemma.scoring.pareto import ScoredEntry, pareto_weights
from lemma.scoring.reputation import apply_ema_to_entries, load_reputation, save_reputation
from lemma.scoring.rewards import entry_from_scores
from lemma.validator import query as q
from lemma.validator.training_export import append_epoch_jsonl, training_record
from lemma.validator.weights_policy import build_full_weights

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def _build_judge(settings: LemmaSettings, dry_run: bool) -> Judge:
    """Return the judge implementation for this epoch.

    ``LEMMA_FAKE_JUDGE=1`` is dry-run only.

    Validator **dry-run** epochs default to ``FakeJudge`` so rehearsal loops stay cheap and deterministic.
    Set ``LEMMA_DRY_RUN_REAL_JUDGE=1`` to use the configured live judge (same HTTP stack as production) while
    still skipping ``set_weights``.
    """
    fake_judge_requested = os.environ.get("LEMMA_FAKE_JUDGE", "").strip().lower() in ("1", "true", "yes")
    if fake_judge_requested and dry_run:
        return FakeJudge()
    if fake_judge_requested:
        raise RuntimeError("LEMMA_FAKE_JUDGE is only allowed for validator dry-run; unset it for live validation")
    use_stub_in_dry = dry_run and os.environ.get("LEMMA_DRY_RUN_REAL_JUDGE", "").strip() != "1"
    if use_stub_in_dry:
        logger.info("dry-run epoch: using FakeJudge (set LEMMA_DRY_RUN_REAL_JUDGE=1 for live judge HTTP)")
        return FakeJudge()
    if dry_run:
        logger.info("LEMMA_DRY_RUN_REAL_JUDGE=1 — using live judge in dry-run (set_weights still skipped)")
    to = float(settings.judge_llm_http_timeout_s or settings.llm_http_timeout_s)
    ra = max(1, int(settings.judge_llm_retry_attempts))
    prov = (settings.judge_provider or "chutes").lower()
    if prov in ("openai", "chutes"):
        key = settings.judge_openai_api_key_resolved()
        if not key:
            raise RuntimeError("JUDGE_OPENAI_API_KEY / OPENAI_API_KEY missing; cannot score live validator epoch")
        return OpenAIJudge(
            key,
            settings.openai_model,
            base_url=settings.openai_base_url,
            temperature=settings.judge_temperature,
            max_tokens=settings.judge_max_tokens,
            timeout=to,
            retry_attempts=ra,
        )
    key = settings.anthropic_api_key
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY missing; cannot score live validator epoch")
    return AnthropicJudge(
        key,
        settings.anthropic_model,
        temperature=settings.judge_temperature,
        max_tokens=settings.judge_max_tokens,
        timeout=to,
        retry_attempts=ra,
    )


def _coldkey_for_uid(metagraph: object, uid: int) -> str:
    cks = getattr(metagraph, "coldkeys", None)
    if cks is None:
        return f"uid:{uid}"
    try:
        v = cks[uid]
        if hasattr(v, "item"):
            return str(v.item())
        return str(v)
    except Exception:
        return f"uid:{uid}"


def _hotkey_ss58_for_uid(metagraph: object, uid: int) -> str | None:
    hks = getattr(metagraph, "hotkeys", None)
    if hks is None:
        return None
    try:
        v = hks[uid]
        if hasattr(v, "item"):
            return str(v.item())
        return str(v)
    except Exception:
        return None


def _merge_multi_round_entries(uid_groups: dict[int, list[ScoredEntry]]) -> list[ScoredEntry]:
    merged: list[ScoredEntry] = []
    for uid, es in uid_groups.items():
        if len(es) == 1:
            merged.append(es[0])
            continue
        rs = sum(e.reasoning_score for e in es) / len(es)
        ts = int(round(sum(e.tokens for e in es) / len(es)))
        cs = sum(e.composite for e in es) / len(es)
        merged.append(
            ScoredEntry(
                uid=uid,
                reasoning_score=rs,
                tokens=ts,
                composite=cs,
                submission_fp="",
            ),
        )
    return merged


async def run_epoch(
    settings: LemmaSettings,
    problem_source: ProblemSource,
    dry_run: bool = False,
) -> dict[int, float]:
    t_epoch = time.perf_counter()
    vc, vh = settings.validator_wallet_names()
    wallet = bt.Wallet(name=vc, hotkey=vh)
    subtensor = get_subtensor(settings)
    netuid = settings.netuid
    cur_block = int(subtensor.get_current_block())
    slack_b = int(settings.lemma_problem_seed_chain_head_slack_blocks or 0)
    seed_head = effective_chain_head_for_problem_seed(cur_block, slack_b)
    metagraph = subtensor.metagraph(netuid)
    raw_n = metagraph.n
    n = int(raw_n.item()) if hasattr(raw_n, "item") else int(raw_n)

    my_uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid)
    if settings.validator_abort_if_not_registered and my_uid is None:
        logger.warning("Validator wallet has no UID on subnet {}; skipping epoch", netuid)
        return {}

    uids = [u for u in range(n) if my_uid is None or u != my_uid]
    if not uids:
        logger.warning("No peer UIDs to query")
        return {}

    logger.debug("canonical judge rubric sha256={}", rubric_sha256())

    problem_seed, problem_seed_tag = resolve_problem_seed(
        chain_head_block=seed_head,
        netuid=netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )

    rep_store = load_reputation(settings.lemma_reputation_state_path)
    judge = _build_judge(settings, dry_run)

    k_problems = max(1, int(settings.lemma_epoch_problem_count))
    aggregate: dict[int, list[ScoredEntry]] = defaultdict(list)
    training_rows: list[dict[str, Any]] = []
    export_path = settings.training_export_jsonl
    export_profile = settings.lemma_training_export_profile

    total_verified = 0
    total_scored = 0
    judge_errors = 0
    judge_parse_rejects = 0
    dedup_dropped = 0
    coldkey_dropped = 0
    deadline_rejects = 0
    attest_rejects = 0
    commit_reveal_rejects = 0
    last_problem: Problem | None = None

    export_lock = asyncio.Lock()

    async with bt.Dendrite(wallet=wallet) as dendrite:
        for sub_k in range(k_problems):
            seed_k = problem_seed if k_problems == 1 else mix_sub_problem_seed(problem_seed, sub_k)
            problem = problem_source.sample(seed=seed_k)
            last_problem = problem

            verify_timeout_s = settings.lean_verify_timeout_s
            wait_scale = 1.0
            if settings.timeout_scale_by_split:
                wait_scale = split_timeout_multiplier(
                    problem.split,
                    settings.timeout_split_easy_mult,
                    settings.timeout_split_medium_mult,
                    settings.timeout_split_hard_mult,
                )
                verify_timeout_s = max(1, int(round(float(settings.lean_verify_timeout_s) * wait_scale)))

            deadline_block, forward_wait_s = compute_forward_deadline_and_wait(
                settings=settings,
                subtensor=subtensor,
                cur_block=seed_head,
                seed_tag=problem_seed_tag,
                wait_scale=wait_scale,
            )

            base_syn: dict[str, object] = {
                "theorem_id": problem.id,
                "theorem_statement": problem.challenge_source(),
                "imports": list(problem.imports),
                "lean_toolchain": problem.lean_toolchain,
                "mathlib_rev": problem.mathlib_rev,
                "deadline_unix": int(time.time()) + int(forward_wait_s),
                "deadline_block": deadline_block,
                "metronome_id": str(seed_k),
                "timeout": forward_wait_s,
            }

            axons = axon_list_for_uids(metagraph, uids)
            commits_by_uid: dict[int, str] = {}
            if settings.lemma_commit_reveal_enabled:
                syn_commit = LemmaChallenge(**base_syn, commit_reveal_phase="commit")
                responses_commit = await q.query_miners(
                    dendrite,
                    axons,
                    syn_commit,
                    timeout=forward_wait_s,
                )
                for uid_c, resp_c in zip(uids, responses_commit, strict=True):
                    if not isinstance(resp_c, LemmaChallenge) or not resp_c.is_success:
                        continue
                    hx = (resp_c.proof_commitment_hex or "").strip()
                    if looks_like_commitment_hex(hx):
                        commits_by_uid[uid_c] = hx.lower().removeprefix("0x")
                synapse = LemmaChallenge(**base_syn, commit_reveal_phase="reveal")
                responses = await q.query_miners(dendrite, axons, synapse, timeout=forward_wait_s)
            else:
                synapse = LemmaChallenge(**base_syn, commit_reveal_phase="off")
                responses = await q.query_miners(dendrite, axons, synapse, timeout=forward_wait_s)
            block_after_query = int(subtensor.get_current_block())

            candidates: list[tuple[int, LemmaChallenge]] = []
            for uid, resp in zip(uids, responses, strict=True):
                if not isinstance(resp, LemmaChallenge):
                    continue
                if not resp.is_success:
                    continue
                if not synapse_miner_response_integrity_ok(resp):
                    logger.warning(
                        "uid={} dropping response: missing/mismatched computed_body_hash or deadline_block "
                        "(tampered payload or miner/validator version skew)",
                        uid,
                    )
                    continue
                db = resp.deadline_block
                if db is not None and block_after_query >= int(db):
                    logger.warning(
                        "uid={} dropping response: chain block {} >= deadline_block {} (late)",
                        uid,
                        block_after_query,
                        db,
                    )
                    deadline_rejects += 1
                    continue
                if not resp.proof_script:
                    continue
                candidates.append((uid, resp))

            if settings.lemma_commit_reveal_enabled:
                filt_cr: list[tuple[int, LemmaChallenge]] = []
                for uid_cr, resp_cr in candidates:
                    exp = commits_by_uid.get(uid_cr)
                    if not exp:
                        commit_reveal_rejects += 1
                        logger.warning(
                            "uid={} dropping reveal: missing commit phase or invalid commit",
                            uid_cr,
                        )
                        continue
                    rblob = reasoning_blob_for_commit(resp_cr.reasoning_trace, resp_cr.reasoning_steps)
                    if not verify_reveal_against_commitment(
                        expected_commitment_hex=exp,
                        theorem_id=resp_cr.theorem_id or "",
                        metronome_id=str(resp_cr.metronome_id or ""),
                        nonce_hex=resp_cr.commit_reveal_nonce_hex or "",
                        proof_script=resp_cr.proof_script or "",
                        reasoning_blob=rblob,
                    ):
                        commit_reveal_rejects += 1
                        logger.warning(
                            "uid={} dropping reveal: commit preimage mismatch",
                            uid_cr,
                        )
                        continue
                    filt_cr.append((uid_cr, resp_cr))
                candidates = filt_cr

            if settings.lemma_miner_verify_attest_enabled:
                filt_att: list[tuple[int, LemmaChallenge]] = []
                for uid_a, resp_a in candidates:
                    sig_a = (resp_a.miner_verify_attest_signature_hex or "").strip()
                    if not sig_a:
                        attest_rejects += 1
                        logger.warning(
                            "uid={} dropping response: miner_verify_attest_signature_hex missing",
                            uid_a,
                        )
                        continue
                    hk_a = _hotkey_ss58_for_uid(metagraph, uid_a)
                    if not hk_a:
                        attest_rejects += 1
                        logger.warning("uid={} dropping response: no metagraph hotkey", uid_a)
                        continue
                    msg_a = miner_verify_attest_message(resp_a)
                    if not verify_miner_verify_attest_signature(
                        hotkey_ss58=hk_a,
                        message=msg_a,
                        signature_hex=sig_a,
                    ):
                        attest_rejects += 1
                        logger.warning(
                            "uid={} dropping response: miner_verify_attest signature invalid",
                            uid_a,
                        )
                        continue
                    filt_att.append((uid_a, resp_a))
                candidates = filt_att

            if not candidates and uids:
                n_ch = sum(1 for r in responses if isinstance(r, LemmaChallenge))
                n_ok = sum(1 for r in responses if isinstance(r, LemmaChallenge) and r.is_success)
                n_proof = sum(
                    1
                    for r in responses
                    if isinstance(r, LemmaChallenge) and r.is_success and (r.proof_script or "").strip()
                )
                logger.warning(
                    "epoch sub_round={}/{} no miner candidates: queried_uids={} lemma_challenge_responses={} "
                    "synapse_success={} success_with_proof={}",
                    sub_k + 1,
                    k_problems,
                    len(uids),
                    n_ch,
                    n_ok,
                    n_proof,
                )

            verify_sem = asyncio.Semaphore(max(1, settings.lemma_lean_verify_max_concurrent))
            spot_frac = (
                float(settings.lemma_miner_verify_attest_spot_verify_fraction)
                if settings.lemma_miner_verify_attest_enabled
                else 1.0
            )

            async def _verify_one(
                uid: int,
                resp: LemmaChallenge,
                *,
                _sem: asyncio.Semaphore = verify_sem,
                _vto: int = verify_timeout_s,
                _prob: Problem = problem,
                _spot_frac: float = spot_frac,
            ) -> tuple[int, LemmaChallenge, VerifyResult] | None:
                if settings.lemma_miner_verify_attest_enabled:
                    if not attest_spot_should_full_verify(
                        uid=uid,
                        theorem_id=_prob.id,
                        metronome_id=str(resp.metronome_id or ""),
                        spot_verify_fraction=_spot_frac,
                    ):
                        return (
                            uid,
                            resp,
                            VerifyResult(passed=True, reason="attest_trusted"),
                        )
                async with _sem:
                    vr = await asyncio.to_thread(
                        run_lean_verify,
                        settings,
                        verify_timeout_s=_vto,
                        problem=_prob,
                        proof_script=resp.proof_script,
                    )
                if not vr.passed:
                    logger.debug("uid={} verify failed: {}", uid, vr.reason)
                    return None
                return (uid, resp, vr)

            verified_results = await asyncio.gather(*[_verify_one(u, r) for u, r in candidates])
            verified = [x for x in verified_results if x is not None]
            total_verified += len(verified)

            vca = float(settings.lemma_reputation_verify_credibility_alpha)
            if not dry_run and vca > 0.0 and candidates:
                ca = max(1e-9, min(1.0, vca))
                passed_uids = {t[0] for t in verified}
                for uid, _resp in candidates:
                    outcome = 1.0 if uid in passed_uids else 0.0
                    old_c = rep_store.credibility_by_uid.get(uid, 1.0)
                    new_c = ca * outcome + (1.0 - ca) * old_c
                    rep_store.credibility_by_uid[uid] = max(0.0, min(1.0, new_c))

            judge_sem = asyncio.Semaphore(max(1, settings.lemma_judge_max_concurrent))

            async def _score_one(
                item: tuple[int, LemmaChallenge, VerifyResult],
                *,
                _jsem: asyncio.Semaphore = judge_sem,
                _theorem_id: str = problem.id,
            ) -> tuple[ScoredEntry | None, str]:
                uid_i, resp_i, _vr = item
                trace_text = effective_reasoning_text(resp_i)
                try:
                    async with _jsem:
                        rubric = await judge.score(
                            resp_i.theorem_statement,
                            trace_text,
                            resp_i.proof_script or "",
                        )
                except ValueError as err_parse:
                    logger.warning("judge parse/validation failed uid={} err={}", uid_i, err_parse)
                    return None, "parse"
                except Exception as err_judge:  # noqa: BLE001
                    logger.warning("judge failed uid={} err={}", uid_i, err_judge)
                    return None, "error"
                if export_path:
                    async with export_lock:
                        training_rows.append(
                            training_record(
                                block=cur_block,
                                theorem_id=_theorem_id,
                                uid=uid_i,
                                resp=resp_i,
                                rubric=rubric,
                                profile=export_profile,
                            ),
                        )
                ent = entry_from_scores(
                    uid_i,
                    rubric,
                    trace_text,
                    theorem_statement=resp_i.theorem_statement,
                    proof_script=resp_i.proof_script or "",
                    proof_weight=settings.lemma_score_proof_weight,
                    token_model=settings.lemma_pareto_token_model,
                    proof_intrinsic_strip_comments=settings.lemma_proof_intrinsic_strip_comments,
                )
                return ent, "ok"

            score_pairs = await asyncio.gather(*[_score_one(v) for v in verified])
            scored_sub: list[ScoredEntry] = []
            for ent, tag in score_pairs:
                if tag == "parse":
                    judge_parse_rejects += 1
                    judge_errors += 1
                elif tag == "error":
                    judge_errors += 1
                elif ent is not None:
                    scored_sub.append(ent)
            total_scored += len(scored_sub)

            if settings.lemma_scoring_dedup_identical and scored_sub:
                scored_sub, ddrop = dedup_identical_submissions(scored_sub, lambda e: e.submission_fp)
                dedup_dropped += ddrop

            for e in scored_sub:
                aggregate[e.uid].append(e)

    scored = _merge_multi_round_entries(aggregate)

    if settings.lemma_scoring_coldkey_dedup and scored:
        scored, ckdrop = dedup_coldkeys(scored, lambda u: _coldkey_for_uid(metagraph, u))
        coldkey_dropped += ckdrop

    alpha = float(settings.lemma_reputation_ema_alpha)
    cred_exp = float(settings.lemma_reputation_credibility_exponent)
    if scored and not dry_run and (alpha > 0.0 or cred_exp > 0.0):
        scored, rep_store.ema_by_uid, _ = apply_ema_to_entries(
            scored,
            alpha=alpha,
            credibility_exponent=cred_exp,
            prev_ema=rep_store.ema_by_uid,
            credibility_by_uid=dict(rep_store.credibility_by_uid),
        )
        try:
            save_reputation(settings.lemma_reputation_state_path, rep_store)
        except OSError as e:
            logger.warning("could not save reputation state: {}", e)

    weights_by_uid = pareto_weights(scored)

    logger.debug(
        "epoch concurrency caps used: LEMMA_LEAN_VERIFY_MAX_CONCURRENT={} LEMMA_JUDGE_MAX_CONCURRENT={} "
        "k_problems={}",
        settings.lemma_lean_verify_max_concurrent,
        settings.lemma_judge_max_concurrent,
        k_problems,
    )

    if export_path and training_rows:
        append_epoch_jsonl(
            export_path,
            training_rows,
            weights_by_uid,
            include_pareto_weights=(export_profile == "full"),
        )
        logger.debug(
            "training_export appended {} rows to {}",
            len(training_rows),
            export_path,
        )

    full_weights, skip_chain_write = build_full_weights(
        n,
        weights_by_uid,
        empty_policy=settings.empty_epoch_weights_policy,
        exclude_uid=my_uid if isinstance(my_uid, int) else None,
    )

    elapsed = time.perf_counter() - t_epoch
    split = last_problem.split if last_problem else "?"
    thm = last_problem.id if last_problem else "?"
    logger.info(
        "lemma_epoch_summary chain_head_block={} problem_seed_chain_head={} problem_seed_slack_blocks={} "
        "problem_seed={} problem_seed_tag={} split={} "
        "theorem_id={} k_problems={} verified={} scored={} pareto_entries={} "
        "judge_errors={} judge_parse_rejects={} dedup_dropped={} coldkey_dropped={} deadline_rejects={} "
        "attest_rejects={} commit_reveal_rejects={} "
        "skip_set_weights={} seconds={:.2f}  "
        "[verified=Lean proof OK; scored=proof+judge blend then EMA/dedup; pareto_entries=weight rows]",
        cur_block,
        seed_head,
        slack_b,
        problem_seed,
        problem_seed_tag,
        split,
        thm,
        k_problems,
        total_verified,
        total_scored,
        len(weights_by_uid),
        judge_errors,
        judge_parse_rejects,
        dedup_dropped,
        coldkey_dropped,
        deadline_rejects,
        attest_rejects,
        commit_reveal_rejects,
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
