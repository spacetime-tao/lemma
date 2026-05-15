"""One validator poll: query miners, verify proofs, update miner weights."""

from __future__ import annotations

import asyncio
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import bittensor as bt
from loguru import logger

from lemma import __version__
from lemma.commitments import commitment_payload_matches, proof_sha256
from lemma.common.config import LemmaSettings
from lemma.common.subtensor import get_subtensor
from lemma.common.synapse_limits import synapse_payload_error
from lemma.lean.sandbox import VerifyResult
from lemma.lean.verify_runner import run_lean_verify
from lemma.ledger import (
    LedgerSolver,
    SolvedLedgerEntry,
    active_solver_weights,
    append_solved_ledger_entry,
    matching_solved_ledger,
    split_solver_weights,
)
from lemma.lifecycle import TargetPhase, target_phase
from lemma.problems.base import Problem, ProblemSource
from lemma.problems.known_theorems import known_theorems_manifest_sha256
from lemma.protocol import LemmaChallenge, synapse_miner_response_integrity_ok


def _validator_poll_challenge(problem: Problem, *, poll_id: str) -> LemmaChallenge:
    return LemmaChallenge(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        poll_id=poll_id,
    )


def _problem_statement_hashes(problem_source: ProblemSource) -> dict[str, str]:
    return {problem.id: problem.theorem_statement_sha256() for problem in problem_source.all_problems()}


@dataclass(frozen=True)
class CommitmentEvidence:
    proof_sha256: str
    commitment_hash: str
    commitment_block: int
    commit_cutoff_block: int


def _hotkey_ss58_for_uid(metagraph: object, uid: int) -> str | None:
    hks = getattr(metagraph, "hotkeys", None)
    if hks is None:
        return None
    try:
        v = hks[uid]
        return str(v.item()) if hasattr(v, "item") else str(v)
    except Exception as e:
        logger.debug("metagraph hotkey lookup failed uid={}: {}", uid, e)
        return None


def _coldkey_for_uid_or_none(metagraph: object, uid: int) -> str | None:
    cks = getattr(metagraph, "coldkeys", None)
    if cks is None:
        return None
    try:
        v = cks[uid]
        s = str(v.item()) if hasattr(v, "item") else str(v)
        return s.strip() or None
    except Exception as e:
        logger.debug("metagraph coldkey lookup failed uid={}: {}", uid, e)
        return None


def _set_weights_outcome(result: object) -> tuple[bool, str]:
    if isinstance(result, (tuple, list)) and result:
        ok = bool(result[0])
        message = "" if len(result) < 2 or result[1] is None else str(result[1])
        return ok, message or ("" if ok else "success=False without message")
    if isinstance(result, dict):
        raw_ok = result.get("success", result.get("ok"))
        ok = bool(result) if raw_ok is None else bool(raw_ok)
        raw_message = result.get("message", result.get("msg", result.get("error")))
        message = "" if raw_message is None else str(raw_message)
        return ok, message or ("" if ok else "success=False without message")
    if isinstance(result, bool):
        return result, "" if result else "False"
    raw_ok = getattr(result, "success", getattr(result, "ok", None))
    ok = bool(result) if raw_ok is None else bool(raw_ok)
    raw_message = getattr(result, "message", getattr(result, "msg", getattr(result, "error", None)))
    message = "" if raw_message is None else str(raw_message)
    return ok, message or ("" if ok else "success=False without message")


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


def _response_matches_poll(resp: LemmaChallenge, problem: Problem, *, poll_id: str) -> bool:
    return (
        resp.theorem_id == problem.id
        and resp.theorem_statement == problem.challenge_source()
        and list(resp.imports or []) == list(problem.imports)
        and resp.lean_toolchain == problem.lean_toolchain
        and resp.mathlib_rev == problem.mathlib_rev
        and resp.poll_id == poll_id
    )


def _full_weights(n: int, weights_by_uid: dict[int, float]) -> tuple[list[float], bool]:
    if not weights_by_uid:
        return [0.0 for _ in range(n)], True
    weights = [0.0 for _ in range(n)]
    total = sum(max(0.0, float(v)) for v in weights_by_uid.values())
    if total <= 0.0:
        return weights, True
    for uid, weight in weights_by_uid.items():
        if 0 <= uid < n:
            weights[uid] = max(0.0, float(weight)) / total
    return weights, False


def _get_all_commitments_at(subtensor: Any, netuid: int, block: int) -> dict[str, str]:
    raw = subtensor.get_all_commitments(netuid, block=block)
    if not isinstance(raw, dict):
        return {}
    return {str(hotkey): str(payload) for hotkey, payload in raw.items()}


def _first_seen_commitment_block(
    subtensor: Any,
    netuid: int,
    *,
    hotkey: str,
    payload: str,
    start_block: int,
    cutoff_block: int,
) -> int | None:
    for block in range(int(start_block), int(cutoff_block) + 1):
        if _get_all_commitments_at(subtensor, netuid, block).get(hotkey) == payload:
            return block
    return None


def _commitment_evidence(
    settings: LemmaSettings,
    subtensor: Any,
    *,
    netuid: int,
    phase: TargetPhase,
    problem: Problem,
    manifest_sha256: str,
    hotkey: str,
    resp: LemmaChallenge,
    commitments_at_cutoff: dict[str, str],
    first_seen_cache: dict[tuple[str, str], int | None],
) -> CommitmentEvidence | None:
    proof = resp.proof_script or ""
    nonce = resp.proof_nonce or ""
    commitment_hash = resp.commitment_hash or ""
    if not proof.strip() or not nonce or not commitment_hash:
        return None
    payload = commitments_at_cutoff.get(hotkey)
    if not payload:
        return None
    proof_hash = proof_sha256(proof)
    if not commitment_payload_matches(
        payload,
        netuid=settings.netuid,
        miner_hotkey=hotkey,
        manifest_sha256=manifest_sha256,
        problem=problem,
        proof_hash=proof_hash,
        nonce=nonce,
        commitment_hash=commitment_hash,
    ):
        return None
    cache_key = (hotkey, payload)
    if cache_key not in first_seen_cache:
        first_seen_cache[cache_key] = _first_seen_commitment_block(
            subtensor,
            netuid,
            hotkey=hotkey,
            payload=payload,
            start_block=phase.target_start_block,
            cutoff_block=phase.commit_cutoff_block,
        )
    first_seen = first_seen_cache[cache_key]
    if first_seen is None:
        return None
    return CommitmentEvidence(
        proof_sha256=proof_hash,
        commitment_hash=commitment_hash,
        commitment_block=first_seen,
        commit_cutoff_block=phase.commit_cutoff_block,
    )


def _select_earliest_commitment_block(
    verified: list[tuple[int, LemmaChallenge, VerifyResult, CommitmentEvidence]],
) -> list[tuple[int, LemmaChallenge, VerifyResult, CommitmentEvidence]]:
    if not verified:
        return []
    earliest_block = min(item[3].commitment_block for item in verified)
    return sorted((item for item in verified if item[3].commitment_block == earliest_block), key=lambda item: item[0])


async def run_epoch(
    settings: LemmaSettings,
    problem_source: ProblemSource,
    dry_run: bool = False,
) -> dict[int, float]:
    t0 = time.perf_counter()
    disk_issue = _disk_preflight_issue(settings)
    if disk_issue:
        logger.error("validator infra skip before miner query: {}", disk_issue)
        return {}

    vc, vh = settings.validator_wallet_names()
    wallet = bt.Wallet(name=vc, hotkey=vh)
    subtensor = get_subtensor(settings)
    netuid = settings.netuid
    cur_block = int(subtensor.get_current_block())
    metagraph = subtensor.metagraph(netuid)
    raw_n = metagraph.n
    n = int(raw_n.item()) if hasattr(raw_n, "item") else int(raw_n)
    my_uid = subtensor.get_uid_for_hotkey_on_subnet(wallet.hotkey.ss58_address, netuid)
    if settings.validator_abort_if_not_registered and my_uid is None:
        logger.warning("Validator wallet has no UID on subnet {}; skipping poll", netuid)
        return {}
    uids = [uid for uid in range(n) if my_uid is None or uid != my_uid]
    if not uids:
        logger.warning("No peer UIDs to query")
        return {}

    statement_hashes = _problem_statement_hashes(problem_source)
    matching_ledger_entries = matching_solved_ledger(settings.solved_ledger_path, statement_hashes)
    try:
        problem = problem_source.sample(seed=0)
    except ValueError:
        weights_by_uid = active_solver_weights(
            settings.solved_ledger_path,
            set(uids),
            statement_hashes,
        )
        logger.info("all known-theorem targets solved; preserving solver weights={}", weights_by_uid)
        return await _write_weights(settings, subtensor, wallet, netuid, n, weights_by_uid, dry_run=dry_run)

    try:
        phase = target_phase(settings, matching_ledger_entries, cur_block)
    except ValueError as exc:
        logger.error("validator cannot run target lifecycle: {}", exc)
        return {}
    if phase.name != "reveal":
        weights_by_uid = active_solver_weights(settings.solved_ledger_path, set(uids), statement_hashes)
        logger.info(
            "target_not_revealable target_id={} phase={} current_block={} reveal_block={}",
            problem.id,
            phase.name,
            phase.current_block,
            phase.reveal_block,
        )
        return await _write_weights(settings, subtensor, wallet, netuid, n, weights_by_uid, dry_run=dry_run)

    poll_id = f"{problem.id}:{cur_block}:{int(time.time())}"
    synapse = _validator_poll_challenge(problem, poll_id=poll_id)

    async with bt.Dendrite(wallet=wallet) as dendrite:
        responses = await dendrite(
            [metagraph.axons[uid] for uid in uids],
            synapse,
            timeout=float(settings.validator_poll_timeout_s),
            run_async=True,
        )

    commitments_at_cutoff = _get_all_commitments_at(subtensor, netuid, phase.commit_cutoff_block)
    first_seen_cache: dict[tuple[str, str], int | None] = {}
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    candidates: list[tuple[int, LemmaChallenge, CommitmentEvidence]] = []
    for uid, resp in zip(uids, responses, strict=True):
        if not isinstance(resp, LemmaChallenge) or not resp.is_success:
            continue
        if not synapse_miner_response_integrity_ok(resp):
            logger.warning("uid={} dropping response: body hash mismatch", uid)
            continue
        if not _response_matches_poll(resp, problem, poll_id=poll_id):
            logger.warning("uid={} dropping response: target fields do not match poll", uid)
            continue
        payload_err = synapse_payload_error(resp, settings)
        if payload_err:
            logger.warning("uid={} dropping response: {}", uid, payload_err)
            continue
        if (resp.proof_script or "").strip():
            hotkey = _hotkey_ss58_for_uid(metagraph, uid)
            if hotkey is None:
                logger.warning("uid={} dropping response: missing hotkey", uid)
                continue
            evidence = _commitment_evidence(
                settings,
                subtensor,
                netuid=netuid,
                phase=phase,
                problem=problem,
                manifest_sha256=manifest_sha,
                hotkey=hotkey,
                resp=resp,
                commitments_at_cutoff=commitments_at_cutoff,
                first_seen_cache=first_seen_cache,
            )
            if evidence is None:
                logger.warning("uid={} dropping response: missing or invalid pre-reveal commitment", uid)
                continue
            candidates.append((uid, resp, evidence))

    verify_sem = asyncio.Semaphore(max(1, int(settings.lemma_lean_verify_max_concurrent)))

    async def verify_one(
        uid: int,
        resp: LemmaChallenge,
        evidence: CommitmentEvidence,
    ) -> tuple[int, LemmaChallenge, VerifyResult, CommitmentEvidence] | None:
        async with verify_sem:
            try:
                vr = await asyncio.to_thread(
                    run_lean_verify,
                    settings,
                    verify_timeout_s=settings.lean_verify_timeout_s,
                    problem=problem,
                    proof_script=resp.proof_script or "",
                )
            except Exception as exc:  # noqa: BLE001
                vr = VerifyResult(passed=False, reason="docker_error", stderr_tail=str(exc)[:8000])
        if not vr.passed:
            logger.debug("uid={} verify failed: {}", uid, vr.reason)
            return None
        return uid, resp, vr, evidence

    raw_verified = await asyncio.gather(*(verify_one(uid, resp, evidence) for uid, resp, evidence in candidates))
    verified = _select_earliest_commitment_block([item for item in raw_verified if item is not None])
    dry_run_solver_weights: dict[int, float] = {}
    if verified:
        solvers = tuple(
            LedgerSolver(
                uid=uid,
                hotkey=_hotkey_ss58_for_uid(metagraph, uid),
                coldkey=_coldkey_for_uid_or_none(metagraph, uid),
                proof_sha256=evidence.proof_sha256,
                verify_reason=vr.reason,
                build_seconds=float(vr.build_seconds),
                proof_script=resp.proof_script or "",
                proof_nonce=resp.proof_nonce,
                commitment_hash=evidence.commitment_hash,
                commitment_block=evidence.commitment_block,
                commit_cutoff_block=evidence.commit_cutoff_block,
            )
            for uid, resp, vr, evidence in sorted(verified, key=lambda item: item[0])
        )
        entry = SolvedLedgerEntry(
            target_id=problem.id,
            solvers=solvers,
            accepted_block=cur_block,
            accepted_unix=int(time.time()),
            validator_hotkey=wallet.hotkey.ss58_address,
            lemma_version=__version__,
            theorem_statement_sha256=problem.theorem_statement_sha256(),
        )
        if dry_run:
            dry_run_solver_weights = split_solver_weights(entry.solver_uids, set(uids))
        else:
            try:
                append_solved_ledger_entry(settings.solved_ledger_path, entry)
                logger.info(
                    "target_solved target_id={} solver_uids={} proofs={}",
                    entry.target_id,
                    list(entry.solver_uids),
                    [solver.proof_sha256 for solver in entry.solvers],
                )
            except ValueError as exc:
                logger.warning("solved ledger append skipped: {}", exc)

    weights_by_uid = active_solver_weights(
        settings.solved_ledger_path,
        set(uids),
        statement_hashes,
    )
    if dry_run and not weights_by_uid and dry_run_solver_weights:
        weights_by_uid = dry_run_solver_weights
    logger.info(
        "lemma_poll_summary block={} target_id={} candidates={} verified={} weight_entries={} seconds={:.2f}",
        cur_block,
        problem.id,
        len(candidates),
        len(verified),
        len(weights_by_uid),
        time.perf_counter() - t0,
    )
    return await _write_weights(settings, subtensor, wallet, netuid, n, weights_by_uid, dry_run=dry_run)


async def _write_weights(
    settings: LemmaSettings,
    subtensor: Any,
    wallet: Any,
    netuid: int,
    n: int,
    weights_by_uid: dict[int, float],
    *,
    dry_run: bool,
) -> dict[int, float]:
    full_weights, skip_chain_write = _full_weights(n, weights_by_uid)
    if dry_run:
        logger.info("DRY RUN weights: {}", weights_by_uid)
        return weights_by_uid
    if skip_chain_write:
        logger.warning("Skipping set_weights (no active weights)")
        return weights_by_uid

    last_success = False
    last_message = ""
    for attempt in range(int(settings.set_weights_max_retries)):
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
        except Exception as exc:  # noqa: BLE001
            last_success = False
            last_message = f"{type(exc).__name__}: {exc}"
        if last_success:
            break
        if attempt_no < int(settings.set_weights_max_retries):
            logger.warning("set_weights attempt {} failed; retrying message={}", attempt_no, last_message)
            await asyncio.sleep(float(settings.set_weights_retry_delay_s) * (2**attempt))
        else:
            logger.error("set_weights attempt {} failed; no retries left message={}", attempt_no, last_message)
    logger.info("set_weights success={} message={}", last_success, last_message)
    return weights_by_uid
