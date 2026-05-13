"""One scoring round: broadcast, verify, score, Pareto, set_weights."""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import time
from collections import defaultdict
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import bittensor as bt
from loguru import logger

from lemma import __version__
from lemma.common.block_deadline import compute_forward_deadline_and_wait
from lemma.common.problem_seed import (
    effective_chain_head_for_problem_seed,
    mix_sub_problem_seed,
    resolve_problem_seed,
)
from lemma.common.subtensor import get_subtensor
from lemma.common.synapse_limits import synapse_payload_error
from lemma.judge.profile import judge_profile_sha256
from lemma.lean.sandbox import VerifyResult
from lemma.lean.verify_runner import run_lean_verify
from lemma.problems.base import Problem, ProblemSource
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.hybrid import problem_supply_registry_sha256
from lemma.protocol import LemmaChallenge, synapse_miner_response_integrity_ok
from lemma.protocol_attest import (
    attest_spot_should_full_verify,
    miner_verify_attest_message,
    verify_miner_verify_attest_signature,
)
from lemma.protocol_commit_reveal import (
    normalize_commitment_hex,
    verify_reveal_against_commitment,
)
from lemma.scoring.dedup import partition_same_coldkey_weights
from lemma.scoring.pareto import ScoredEntry, pareto_weights
from lemma.scoring.reputation import apply_ema_to_entries, load_reputation, save_reputation
from lemma.scoring.rewards import entry_from_verified_proof
from lemma.validator.training_export import append_epoch_jsonl, round_summary_record, training_record
from lemma.validator.weights_policy import build_full_weights

if TYPE_CHECKING:
    from lemma.common.config import LemmaSettings


def _validator_broadcast_challenge(
    problem: Problem,
    *,
    seed_k: int,
    deadline_block: int | None,
    forward_wait_s: float,
    commit_reveal_phase: str,
) -> LemmaChallenge:
    """Build the validator→miner synapse for one broadcast (commit/reveal/off)."""
    return LemmaChallenge(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        deadline_unix=int(time.time()) + int(forward_wait_s),
        deadline_block=deadline_block,
        metronome_id=str(seed_k),
        timeout=float(forward_wait_s),
        commit_reveal_phase=commit_reveal_phase,
    )


def _coldkey_for_uid(metagraph: object, uid: int) -> str:
    return _coldkey_for_uid_or_none(metagraph, uid) or f"uid:{uid}"


def _coldkey_for_uid_or_none(metagraph: object, uid: int) -> str | None:
    cks = getattr(metagraph, "coldkeys", None)
    if cks is None:
        return None
    try:
        v = cks[uid]
        if hasattr(v, "item"):
            v = v.item()
        s = str(v).strip()
        return s or None
    except Exception as e:
        logger.debug("metagraph coldkey lookup failed uid={}: {}", uid, e)
        return None


def _hotkey_ss58_for_uid(metagraph: object, uid: int) -> str | None:
    hks = getattr(metagraph, "hotkeys", None)
    if hks is None:
        return None
    try:
        v = hks[uid]
        if hasattr(v, "item"):
            return str(v.item())
        return str(v)
    except Exception as e:
        logger.debug("metagraph hotkey lookup failed uid={}: {}", uid, e)
        return None


def _response_matches_problem_challenge(
    resp: LemmaChallenge,
    problem: Problem,
    *,
    metronome_id: str,
    deadline_block: int | None,
) -> bool:
    if resp.theorem_id != problem.id:
        return False
    if resp.theorem_statement != problem.challenge_source():
        return False
    if list(resp.imports or []) != list(problem.imports):
        return False
    if resp.lean_toolchain != problem.lean_toolchain:
        return False
    if resp.mathlib_rev != problem.mathlib_rev:
        return False
    if str(resp.metronome_id or "") != str(metronome_id):
        return False
    if resp.deadline_block is None or deadline_block is None:
        return False
    return int(resp.deadline_block) == int(deadline_block)


def _response_status_summary(responses: list[Any]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for resp in responses:
        axon = getattr(resp, "axon", None)
        dendrite = getattr(resp, "dendrite", None)
        code = getattr(dendrite, "status_code", None) or getattr(axon, "status_code", None)
        msg = getattr(dendrite, "status_message", None) or getattr(axon, "status_message", None) or ""
        msg = " ".join(str(msg).split())[:96]
        key = f"{code} {msg}".strip() if code or msg else f"type={type(resp).__name__}"
        counts[key] += 1
    return "; ".join(f"{n}x {key}" for key, n in sorted(counts.items()))


def _short_repr(value: object, *, limit: int = 300) -> str:
    text = " ".join(repr(value).split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _set_weights_outcome(result: object) -> tuple[bool, str]:
    if isinstance(result, (tuple, list)) and result:
        ok = bool(result[0])
        message = "" if len(result) < 2 or result[1] is None else str(result[1])
        return ok, message or ("" if ok else _short_repr(result))
    if isinstance(result, dict):
        raw_ok = result.get("success", result.get("ok"))
        ok = bool(result) if raw_ok is None else bool(raw_ok)
        raw_message = result.get("message", result.get("msg", result.get("error")))
        message = "" if raw_message is None else str(raw_message)
        return ok, message or ("" if ok else _short_repr(result))
    if isinstance(result, bool):
        return result, "" if result else "False"

    raw_ok = getattr(result, "success", getattr(result, "ok", None))
    ok = bool(result) if raw_ok is None else bool(raw_ok)
    raw_message = getattr(result, "message", getattr(result, "msg", getattr(result, "error", None)))
    message = "" if raw_message is None else str(raw_message)
    return ok, message or ("" if ok else _short_repr(result))


def _merge_multi_round_entries(uid_groups: dict[int, list[ScoredEntry]]) -> list[ScoredEntry]:
    merged: list[ScoredEntry] = []
    for uid, es in uid_groups.items():
        if len(es) == 1:
            merged.append(es[0])
            continue
        rs = sum(e.score for e in es) / len(es)
        ts = int(round(sum(e.cost for e in es) / len(es)))
        merged.append(
            ScoredEntry(
                uid=uid,
                score=rs,
                cost=ts,
                submission_fp="",
            ),
        )
    return merged


def _update_verify_credibility(
    credibility_by_uid: dict[int, float],
    candidates: list[tuple[int, LemmaChallenge]],
    verified: list[tuple[int, LemmaChallenge, VerifyResult]],
    *,
    alpha: float,
) -> None:
    ca = max(1e-9, min(1.0, float(alpha)))
    attest_trusted_uids = {uid for uid, _resp, vr in verified if vr.reason == "attest_trusted"}
    verified_by_validator_uids = {uid for uid, _resp, vr in verified if vr.reason != "attest_trusted"}
    for uid, _resp in candidates:
        if uid in attest_trusted_uids:
            continue
        outcome = 1.0 if uid in verified_by_validator_uids else 0.0
        old_c = credibility_by_uid.get(uid, 1.0)
        new_c = ca * outcome + (1.0 - ca) * old_c
        credibility_by_uid[uid] = max(0.0, min(1.0, new_c))


VerifyItem = tuple[int, LemmaChallenge, VerifyResult]

_VERIFY_INFRA_REASONS = frozenset({"timeout", "oom", "docker_error", "remote_error"})


def _verify_result_is_infra_failure(vr: VerifyResult) -> bool:
    return not vr.passed and vr.reason in _VERIFY_INFRA_REASONS


def _existing_disk_path(path: Path) -> Path:
    p = path.expanduser()
    if p.exists():
        return p
    for parent in p.parents:
        if parent.exists():
            return parent
    return Path("/")


def _disk_preflight_issue(settings: LemmaSettings) -> str | None:
    min_free = int(settings.validator_min_free_bytes or 0)
    if min_free <= 0:
        return None
    paths = [Path("/")]
    if settings.lean_verify_workspace_cache_dir is not None:
        paths.append(Path(settings.lean_verify_workspace_cache_dir))
    checked: set[str] = set()
    for raw_path in paths:
        path = _existing_disk_path(raw_path)
        key = str(path.resolve())
        if key in checked:
            continue
        checked.add(key)
        try:
            free = int(shutil.disk_usage(path).free)
        except OSError as e:
            return f"disk preflight could not inspect {path}: {e}"
        if free < min_free:
            return f"disk preflight free_bytes={free} below_min={min_free} path={path}"
    return None


def _lean_verify_equivalence_key(resp: LemmaChallenge) -> str:
    """Hash fields that determine Lean verification for one already-bound challenge response."""
    h = hashlib.sha256()
    for part in (
        resp.theorem_id or "",
        resp.theorem_statement or "",
        "\n".join(resp.imports or []),
        resp.lean_toolchain or "",
        resp.mathlib_rev or "",
        resp.proof_script or "",
    ):
        h.update(part.encode("utf-8"))
        h.update(b"\x1e")
    return h.hexdigest()


async def _run_verify_batch(
    candidates: list[tuple[int, LemmaChallenge]],
    verify_one: Callable[[int, LemmaChallenge], Awaitable[VerifyItem | None]],
    *,
    key_fn: Callable[[int, LemmaChallenge], str] | None = None,
) -> list[VerifyItem]:
    """Run verifier tasks while isolating unexpected per-miner failures."""
    verify_inputs = candidates
    groups: list[list[tuple[int, LemmaChallenge]]] | None = None
    if key_fn is not None and len(candidates) > 1:
        grouped: dict[str, list[tuple[int, LemmaChallenge]]] = {}
        for uid, resp in candidates:
            grouped.setdefault(key_fn(uid, resp), []).append((uid, resp))
        if len(grouped) < len(candidates):
            groups = list(grouped.values())
            verify_inputs = [g[0] for g in groups]
            logger.debug(
                "lean verify reuse: candidates={} unique_payloads={} reused_results={}",
                len(candidates),
                len(verify_inputs),
                len(candidates) - len(verify_inputs),
            )

    results = await asyncio.gather(
        *(verify_one(uid, resp) for uid, resp in verify_inputs),
        return_exceptions=True,
    )
    verified: list[VerifyItem] = []
    for idx, ((uid, _resp), raw) in enumerate(zip(verify_inputs, results, strict=True)):
        if isinstance(raw, BaseException):
            if isinstance(raw, Exception):
                logger.warning("uid={} verify task failed: {}", uid, raw)
            continue
        result: VerifyItem | None = raw
        if result is not None:
            if groups is None:
                verified.append(result)
                continue
            _src_uid, _src_resp, vr = result
            for group_uid, group_resp in groups[idx]:
                verified.append((group_uid, group_resp, vr.model_copy()))
    return verified


async def run_epoch(
    settings: LemmaSettings,
    problem_source: ProblemSource,
    dry_run: bool = False,
) -> dict[int, float]:
    t_epoch = time.perf_counter()
    disk_issue = _disk_preflight_issue(settings)
    if disk_issue:
        logger.error("validator infra skip before miner query: {}", disk_issue)
        return {}

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

    problem_seed, problem_seed_tag = resolve_problem_seed(
        chain_head_block=seed_head,
        netuid=netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )

    rep_store = load_reputation(settings.lemma_reputation_state_path)
    rep_dirty = False

    k_problems = max(1, int(settings.lemma_epoch_problem_count))
    aggregate: dict[int, list[ScoredEntry]] = defaultdict(list)
    training_rows: list[dict[str, Any]] = []
    export_path = settings.training_export_jsonl
    export_profile = settings.lemma_training_export_profile
    export_context = (
        {
            "lemma_version": __version__,
            "judge_profile_sha256": judge_profile_sha256(settings),
            "generated_registry_sha256": generated_registry_sha256(),
            "problem_supply_registry_sha256": problem_supply_registry_sha256(
                generated_weight=settings.lemma_hybrid_generated_weight,
                catalog_weight=settings.lemma_hybrid_catalog_weight,
            ),
        }
        if export_path
        else None
    )

    total_verified = 0
    total_scored = 0
    coldkey_partitioned = 0
    deadline_rejects = 0
    challenge_rejects = 0
    payload_rejects = 0
    attest_rejects = 0
    commit_reveal_rejects = 0
    verify_infra_errors = 0
    verify_infra_error_uids: set[int] = set()
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
                wait_scale = float(
                    {
                        "easy": settings.timeout_split_easy_mult,
                        "medium": settings.timeout_split_medium_mult,
                        "hard": settings.timeout_split_hard_mult,
                    }.get((problem.split or "").strip().lower(), 1.0)
                )
                verify_timeout_s = max(1, int(round(float(settings.lean_verify_timeout_s) * wait_scale)))

            deadline_block, forward_wait_s = compute_forward_deadline_and_wait(
                settings=settings,
                subtensor=subtensor,
                cur_block=seed_head,
                seed_tag=problem_seed_tag,
                wait_scale=wait_scale,
            )

            axons = [metagraph.axons[uid] for uid in uids]
            commits_by_uid: dict[int, str] = {}
            if settings.lemma_commit_reveal_enabled:
                syn_commit = _validator_broadcast_challenge(
                    problem,
                    seed_k=seed_k,
                    deadline_block=deadline_block,
                    forward_wait_s=float(forward_wait_s),
                    commit_reveal_phase="commit",
                )
                responses_commit = await dendrite(
                    axons,
                    syn_commit,
                    timeout=forward_wait_s,
                    run_async=True,
                )
                for uid_c, resp_c in zip(uids, responses_commit, strict=True):
                    if not isinstance(resp_c, LemmaChallenge) or not resp_c.is_success:
                        continue
                    hx = (resp_c.proof_commitment_hex or "").strip()
                    norm_commit = normalize_commitment_hex(hx)
                    if norm_commit is not None:
                        commits_by_uid[uid_c] = norm_commit
                synapse = _validator_broadcast_challenge(
                    problem,
                    seed_k=seed_k,
                    deadline_block=deadline_block,
                    forward_wait_s=float(forward_wait_s),
                    commit_reveal_phase="reveal",
                )
                responses = await dendrite(axons, synapse, timeout=forward_wait_s, run_async=True)
            else:
                synapse = _validator_broadcast_challenge(
                    problem,
                    seed_k=seed_k,
                    deadline_block=deadline_block,
                    forward_wait_s=float(forward_wait_s),
                    commit_reveal_phase="off",
                )
                responses = await dendrite(axons, synapse, timeout=forward_wait_s, run_async=True)
            # Dendrite returns a batch, not a trusted per-response receipt block. Enforce the response deadline
            # conservatively at the block observed after the batch returns.
            batch_block_after_query = int(subtensor.get_current_block())

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
                if not _response_matches_problem_challenge(
                    resp,
                    problem,
                    metronome_id=str(seed_k),
                    deadline_block=deadline_block,
                ):
                    logger.warning(
                        "uid={} dropping response: challenge fields do not match current theorem/metronome",
                        uid,
                    )
                    challenge_rejects += 1
                    continue
                db = resp.deadline_block
                if db is not None and batch_block_after_query >= int(db):
                    logger.warning(
                        "uid={} dropping response: chain block {} >= deadline_block {} (late)",
                        uid,
                        batch_block_after_query,
                        db,
                    )
                    deadline_rejects += 1
                    continue
                payload_err = synapse_payload_error(resp, settings)
                if payload_err:
                    logger.warning("uid={} dropping response: {}", uid, payload_err)
                    payload_rejects += 1
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
                    if not verify_reveal_against_commitment(
                        expected_commitment_hex=exp,
                        theorem_id=resp_cr.theorem_id or "",
                        metronome_id=str(resp_cr.metronome_id or ""),
                        nonce_hex=resp_cr.commit_reveal_nonce_hex or "",
                        proof_script=resp_cr.proof_script or "",
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
                    msg_a = miner_verify_attest_message(
                        resp_a,
                        validator_hotkey=wallet.hotkey.ss58_address,
                    )
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
                    "synapse_success={} success_with_proof={} status_summary={}",
                    sub_k + 1,
                    k_problems,
                    len(uids),
                    n_ch,
                    n_ok,
                    n_proof,
                    _response_status_summary(list(responses)),
                )

            verify_sem = asyncio.Semaphore(max(1, settings.lemma_lean_verify_max_concurrent))
            spot_frac = (
                float(settings.lemma_miner_verify_attest_spot_verify_fraction)
                if settings.lemma_miner_verify_attest_enabled
                else 1.0
            )
            spot_salt = str(settings.lemma_miner_verify_attest_spot_verify_salt or "")

            async def _verify_one(
                uid: int,
                resp: LemmaChallenge,
                *,
                _sem: asyncio.Semaphore = verify_sem,
                _vto: int = verify_timeout_s,
                _prob: Problem = problem,
                _spot_frac: float = spot_frac,
                _spot_salt: str = spot_salt,
            ) -> tuple[int, LemmaChallenge, VerifyResult] | None:
                if settings.lemma_miner_verify_attest_enabled:
                    if not attest_spot_should_full_verify(
                        uid=uid,
                        theorem_id=_prob.id,
                        metronome_id=str(resp.metronome_id or ""),
                        spot_verify_fraction=_spot_frac,
                        spot_verify_salt=_spot_salt,
                    ):
                        return (
                            uid,
                            resp,
                            VerifyResult(passed=True, reason="attest_trusted"),
                        )
                proof_src = resp.proof_script
                if proof_src is None:
                    return None
                async with _sem:
                    try:
                        vr = await asyncio.to_thread(
                            run_lean_verify,
                            settings,
                            verify_timeout_s=_vto,
                            problem=_prob,
                            proof_script=proof_src,
                        )
                    except Exception as exc:  # noqa: BLE001
                        err = str(exc)
                        logger.warning("uid={} verify task raised before VerifyResult: {}", uid, err)
                        vr = VerifyResult(passed=False, reason="docker_error", stderr_tail=err[:8000])
                if _verify_result_is_infra_failure(vr):
                    logger.warning("uid={} verify infra failure: {}", uid, vr.reason)
                    return (uid, resp, vr)
                if not vr.passed:
                    logger.debug("uid={} verify failed: {}", uid, vr.reason)
                    return None
                return (uid, resp, vr)

            verify_key_fn: Callable[[int, LemmaChallenge], str] | None = None
            if not settings.lemma_miner_verify_attest_enabled:

                def verify_key_fn(_uid: int, resp: LemmaChallenge) -> str:
                    return _lean_verify_equivalence_key(resp)

            verify_results = await _run_verify_batch(candidates, _verify_one, key_fn=verify_key_fn)
            verified = [(uid, resp, vr) for uid, resp, vr in verify_results if vr.passed]
            infra_failures = [
                (uid, resp, vr)
                for uid, resp, vr in verify_results
                if _verify_result_is_infra_failure(vr)
            ]
            verify_infra_errors += len(infra_failures)
            verify_infra_error_uids.update(uid for uid, _resp, _vr in infra_failures)
            total_verified += len(verified)

            vca = float(settings.lemma_reputation_verify_credibility_alpha)
            if not dry_run and vca > 0.0 and candidates:
                infra_uids = {uid for uid, _resp, _vr in infra_failures}
                credibility_candidates = [(uid, resp) for uid, resp in candidates if uid not in infra_uids]
                _update_verify_credibility(
                    rep_store.credibility_by_uid,
                    credibility_candidates,
                    verified,
                    alpha=vca,
                )
                rep_dirty = rep_dirty or bool(credibility_candidates)

            scored_sub: list[ScoredEntry] = []
            for uid_i, resp_i, vr_i in verified:
                if export_path:
                    async with export_lock:
                        training_rows.append(
                            training_record(
                                block=cur_block,
                                theorem_id=problem.id,
                                uid=uid_i,
                                resp=resp_i,
                                profile=export_profile,
                                proof_metrics=vr_i.proof_metrics,
                                coldkey=_coldkey_for_uid_or_none(metagraph, uid_i),
                                export_context=export_context,
                            ),
                        )
                scored_sub.append(
                    entry_from_verified_proof(
                        uid_i,
                        theorem_statement=resp_i.theorem_statement,
                        proof_script=resp_i.proof_script or "",
                    ),
                )
            total_scored += len(scored_sub)

            for e in scored_sub:
                aggregate[e.uid].append(e)

    scored = _merge_multi_round_entries(aggregate)

    alpha = float(settings.lemma_reputation_ema_alpha)
    cred_exp = float(settings.lemma_reputation_credibility_exponent)
    if scored and not dry_run and (alpha > 0.0 or cred_exp > 0.0):
        scored, rep_store.ema_by_uid = apply_ema_to_entries(
            scored,
            alpha=alpha,
            credibility_exponent=cred_exp,
            prev_ema=rep_store.ema_by_uid,
            credibility_by_uid=dict(rep_store.credibility_by_uid),
        )
        rep_dirty = True

    if rep_dirty and not dry_run:
        try:
            save_reputation(settings.lemma_reputation_state_path, rep_store)
        except OSError as e:
            logger.warning("could not save reputation state: {}", e)

    weights_by_uid = pareto_weights(scored)
    if settings.lemma_scoring_coldkey_partition and weights_by_uid:
        weights_by_uid, coldkey_partitioned = partition_same_coldkey_weights(
            weights_by_uid,
            lambda u: _coldkey_for_uid(metagraph, u),
        )

    logger.debug(
        "epoch concurrency caps used: LEMMA_LEAN_VERIFY_MAX_CONCURRENT={} k_problems={}",
        settings.lemma_lean_verify_max_concurrent,
        k_problems,
    )

    if export_path and last_problem:
        export_rows = [
            *training_rows,
            round_summary_record(
                block=cur_block,
                theorem_id=last_problem.id,
                passed_uids={e.uid for e in scored},
                verify_infra_error_uids=verify_infra_error_uids,
                export_context=export_context,
            ),
        ]
        try:
            append_epoch_jsonl(
                export_path,
                export_rows,
                weights_by_uid,
                include_pareto_weights=(export_profile == "full"),
            )
            logger.debug(
                "training_export appended {} proof rows and 1 round summary to {}",
                len(training_rows),
                export_path,
            )
        except OSError as e:
            logger.error("training_export append failed after scoring; continuing to set_weights: {}", e)

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
        "coldkey_partitioned={} deadline_rejects={} "
        "challenge_rejects={} payload_rejects={} "
        "attest_rejects={} commit_reveal_rejects={} verify_infra_errors={} "
        "skip_set_weights={} seconds={:.2f}  "
        "[verified=Lean proof OK; scored=verified proof rows; pareto_entries=weight rows]",
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
        coldkey_partitioned,
        deadline_rejects,
        challenge_rejects,
        payload_rejects,
        attest_rejects,
        commit_reveal_rejects,
        verify_infra_errors,
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
    last_success = False
    last_message = ""
    max_retries = settings.set_weights_max_retries
    for attempt in range(max_retries):
        attempt_no = attempt + 1
        try:
            out = subtensor.set_weights(
                wallet=wallet,
                netuid=netuid,
                uids=list(range(n)),
                weights=full_weights,
                wait_for_inclusion=False,
                wait_for_finalization=False,
            )
            last_success, last_message = _set_weights_outcome(out)
        except Exception as e:
            last_success = False
            last_message = f"{type(e).__name__}: {e}"
        if last_success:
            break
        if attempt_no < max_retries:
            logger.warning(
                "set_weights attempt {}/{} failed; retrying message={}",
                attempt_no,
                max_retries,
                last_message,
            )
            await asyncio.sleep(delay * (2**attempt))
        else:
            logger.error(
                "set_weights attempt {}/{} failed; no retries left message={}",
                attempt_no,
                max_retries,
                last_message,
            )

    logger.info(
        "set_weights success={} message={}",
        last_success,
        last_message,
    )
    return weights_by_uid
