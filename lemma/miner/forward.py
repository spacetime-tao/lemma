"""Axon forward handler.

Each validator query runs the prover as soon as the synapse passes gating — no intentional delay
waiting for block/time windows (manual ``lemma-cli try-prover`` is separate and operator-triggered).
"""

import asyncio
import secrets
import threading
import time

from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.lean.verify_runner import run_lean_verify
from lemma.miner.daily_budget import allow_daily_forward
from lemma.miner.gating import MetagraphCache, metagraph_incentive_for_hotkey
from lemma.miner.limits import reject_synopsis, synapse_payload_error
from lemma.miner.prover import Prover
from lemma.problems.factory import resolve_problem
from lemma.protocol import LemmaChallenge
from lemma.protocol_attest import miner_verify_attest_message, sign_miner_verify_attest
from lemma.protocol_commit_reveal import (
    commit_preimage_v1,
    commitment_hex_from_preimage,
    reasoning_blob_for_commit,
)

_COMMIT_REVEAL_CACHE_TTL_S = 900.0
_COMMIT_REVEAL_CACHE_MAX_ENTRIES = 512
_CommitRevealKey = tuple[str, str, str]
_CommitRevealEntry = tuple[float, str, str, str, list | None]
_CommitRevealValue = tuple[str, str, str, list | None]


def _commit_reveal_cache_key(synapse: LemmaChallenge) -> _CommitRevealKey | None:
    validator_hotkey = str(getattr(getattr(synapse, "dendrite", None), "hotkey", "") or "").strip()
    if not validator_hotkey:
        return None
    return (
        validator_hotkey,
        str(synapse.theorem_id or ""),
        str(synapse.metronome_id or ""),
    )


def _with_computed_body_hash(synapse: LemmaChallenge) -> LemmaChallenge:
    return synapse.model_copy(update={"computed_body_hash": synapse.body_hash})


class CommitRevealCache:
    def __init__(
        self,
        *,
        ttl_s: float = _COMMIT_REVEAL_CACHE_TTL_S,
        max_entries: int = _COMMIT_REVEAL_CACHE_MAX_ENTRIES,
    ) -> None:
        self._ttl_s = max(1.0, float(ttl_s))
        self._max_entries = max(1, int(max_entries))
        self._lock = threading.Lock()
        self._entries: dict[_CommitRevealKey, _CommitRevealEntry] = {}

    def _prune_unlocked(self, ts: float) -> None:
        expired = [key for key, entry in self._entries.items() if entry[0] <= ts]
        for key in expired:
            self._entries.pop(key, None)
        while len(self._entries) > self._max_entries:
            oldest = min(self._entries, key=lambda key: self._entries[key][0])
            self._entries.pop(oldest, None)

    def store(
        self,
        key: _CommitRevealKey,
        value: _CommitRevealValue,
        *,
        now: float | None = None,
    ) -> None:
        ts = time.time() if now is None else float(now)
        with self._lock:
            self._prune_unlocked(ts)
            self._entries[key] = (ts + self._ttl_s, *value)
            self._prune_unlocked(ts)

    def pop(
        self,
        key: _CommitRevealKey,
        *,
        now: float | None = None,
    ) -> _CommitRevealValue | None:
        ts = time.time() if now is None else float(now)
        with self._lock:
            self._prune_unlocked(ts)
            entry = self._entries.pop(key, None)
        if entry is None:
            return None
        _expires_at, nonce_hex, proof, trace, steps = entry
        return nonce_hex, proof, trace, steps


def _optional_chain_head(settings: LemmaSettings) -> int | None:
    try:
        from lemma.common.subtensor import get_subtensor

        return int(get_subtensor(settings).get_current_block())
    except Exception:
        return None


def _excerpt(text: str, max_chars: int = 12_000) -> str:
    if len(text) <= max_chars:
        return text
    half = max_chars // 2
    return text[:half] + "\n... [truncated] ...\n" + text[-half:]


def make_forward(
    settings: LemmaSettings,
    prover: Prover,
    *,
    metagraph_cache: MetagraphCache | None = None,
    miner_hotkey_ss58: str | None = None,
    wallet: object | None = None,
    commit_reveal_cache: CommitRevealCache | None = None,
):
    sem = asyncio.Semaphore(max(1, settings.miner_max_concurrent_forwards))
    stats_lock = threading.Lock()
    stats: dict[str, float | int] = {"forwards": 0, "local_ok": 0, "local_fail": 0, "solve_s_total": 0.0}
    cr_cache = commit_reveal_cache or CommitRevealCache()

    async def forward(synapse: LemmaChallenge) -> LemmaChallenge:
        err = synapse_payload_error(synapse, settings, response=False)
        if err:
            return reject_synopsis(synapse, 413, err)

        db = synapse.deadline_block
        if (
            db is not None
            and db > 0
            and settings.miner_reject_past_deadline_block
        ):
            try:
                from lemma.common.subtensor import get_subtensor

                head = int(get_subtensor(settings).get_current_block())
                if head >= db:
                    return reject_synopsis(
                        synapse,
                        400,
                        f"too late for this challenge (chain_head={head} >= deadline_block={db})",
                    )
            except Exception as e:  # noqa: BLE001 — RPC optional
                logger.warning("deadline_block check skipped: {}", e)

        if settings.miner_max_forwards_per_day > 0 and not allow_daily_forward(settings.miner_max_forwards_per_day):
            return reject_synopsis(
                synapse,
                429,
                f"daily forward limit reached ({settings.miner_max_forwards_per_day}/UTC day)",
            )

        my_uid_s = "?"
        my_inc_s = "?"
        if metagraph_cache is not None and miner_hotkey_ss58:
            try:
                uid_i, inc_f = metagraph_incentive_for_hotkey(metagraph_cache, miner_hotkey_ss58)
                if uid_i is not None:
                    my_uid_s = str(uid_i)
                if inc_f is not None:
                    my_inc_s = f"{inc_f:.4f}"
            except Exception as e:  # noqa: BLE001
                logger.debug("miner forward incentive snapshot skipped: {}", e)

        if settings.miner_forward_timeline:
            head = _optional_chain_head(settings)
            dbv = synapse.deadline_block
            bleft: int | str = "?"
            if head is not None and dbv is not None and int(dbv) > 0:
                bleft = max(0, int(dbv) - int(head))
            budget = float(getattr(synapse, "timeout", 0) or 0)
            du = int(synapse.deadline_unix) if synapse.deadline_unix else 0
            wall_deadline_in = max(0.0, float(du) - time.time()) if du else 0.0
            preview = (synapse.theorem_statement or "").replace("\n", " ").strip()
            if len(preview) > 200:
                preview = preview[:197] + "…"
            logger.info(
                "miner timeline 1 RECEIVE theorem_id={} metronome_id={} deadline_block={} chain_head={} "
                "blocks_to_deadline={} axon_http_budget_s={:.0f} wall_deadline_in_s={:.0f} my_uid={} my_incentive={} "
                "statement_preview={!r}",
                synapse.theorem_id,
                synapse.metronome_id,
                dbv if dbv is not None else None,
                head,
                bleft,
                budget,
                wall_deadline_in,
                my_uid_s,
                my_inc_s,
                preview,
            )
        else:
            logger.info(
                "miner forward: solving theorem_id={} metronome_id={} my_uid={} my_incentive={}",
                synapse.theorem_id,
                synapse.metronome_id,
                my_uid_s,
                my_inc_s,
            )
        phase = (synapse.commit_reveal_phase or "off").strip().lower()
        cr_key = None
        if phase in ("commit", "reveal"):
            cr_key = _commit_reveal_cache_key(synapse)
            if cr_key is None:
                return reject_synopsis(
                    synapse,
                    400,
                    "commit-reveal requires validator dendrite hotkey",
                )
        solve_s = 0.0
        trace, proof, steps = "", "", None
        if phase == "reveal":
            cached = cr_cache.pop(cr_key)
            if cached is None:
                return reject_synopsis(
                    synapse,
                    400,
                    "commit-reveal: reveal phase but no cached commit entry",
                )
            nonce_hex, proof, trace, steps = cached
            synapse.commit_reveal_nonce_hex = nonce_hex
        else:
            t0 = time.perf_counter()
            async with sem:
                trace, proof, steps = await prover.solve(synapse)
            solve_s = time.perf_counter() - t0

        if settings.miner_forward_timeline:
            if phase == "reveal":
                logger.info(
                    "miner timeline 2 REVEAL theorem_id={} metronome_id={} proof_chars={} trace_chars={}",
                    synapse.theorem_id,
                    synapse.metronome_id,
                    len(proof or ""),
                    len(trace or ""),
                )
            else:
                logger.info(
                    "miner timeline 2 SOLVED theorem_id={} prover_s={:.2f}s proof_chars={} trace_chars={}",
                    synapse.theorem_id,
                    solve_s,
                    len(proof or ""),
                    len(trace or ""),
                )

        prob_meta = None
        split = "?"
        template_fn = ""
        try:
            prob_meta = resolve_problem(settings, synapse.theorem_id)
            split = prob_meta.split
            ex = prob_meta.extra or {}
            if isinstance(ex, dict) and ex.get("template_fn"):
                template_fn = str(ex.get("template_fn"))
        except Exception:  # noqa: BLE001
            pass

        if settings.miner_log_forwards:
            logger.info(
                "miner forward theorem_id={} trace_chars={} proof_chars={}",
                synapse.theorem_id,
                len(trace or ""),
                len(proof or ""),
            )
            logger.info("reasoning (excerpt):\n{}", _excerpt(trace or ""))
            logger.info("proof_script (excerpt):\n{}", _excerpt(proof or ""))

        local_tag = ""
        local_lean_status = "off"
        if settings.miner_local_verify:
            if not (proof or "").strip():
                local_lean_status = "skipped_empty_proof"
            elif prob_meta is None:
                local_lean_status = "skipped_no_problem"
            else:
                try:
                    vr = await asyncio.to_thread(
                        run_lean_verify,
                        settings,
                        verify_timeout_s=settings.lean_verify_timeout_s,
                        problem=prob_meta,
                        proof_script=proof,
                    )
                    if vr.passed:
                        local_tag = "local_lean=PASS"
                        local_lean_status = "PASS"
                        with stats_lock:
                            stats["local_ok"] = int(stats["local_ok"]) + 1
                        logger.info(
                            "miner local verify OK theorem_id={} build_s={:.2f}",
                            synapse.theorem_id,
                            vr.build_seconds,
                        )
                    else:
                        local_tag = "local_lean=FAIL"
                        local_lean_status = "FAIL"
                        with stats_lock:
                            stats["local_fail"] = int(stats["local_fail"]) + 1
                        logger.warning(
                            "miner local verify FAIL theorem_id={} reason={} build_s={:.2f}",
                            synapse.theorem_id,
                            vr.reason,
                            vr.build_seconds,
                        )
                        logger.warning("stderr_tail:\n{}", _excerpt(vr.stderr_tail or "", 8000))
                except Exception as e:  # noqa: BLE001
                    local_lean_status = "ERROR"
                    logger.warning("miner local verify error theorem_id={}: {}", synapse.theorem_id, e)

        if settings.miner_forward_timeline:
            if settings.miner_local_verify:
                logger.info(
                    "miner timeline 3 OUTCOME theorem_id={} local_lean={} "
                    "(Lean on this machine like validators; judge scores are not returned on the axon)",
                    synapse.theorem_id,
                    local_lean_status,
                )
            else:
                logger.info(
                    "miner timeline 3 OUTCOME theorem_id={} local_lean=off — "
                    "set LEMMA_MINER_LOCAL_VERIFY=1 for Lean PASS/FAIL here; "
                    "validator judge + final weighting stay off-axon",
                    synapse.theorem_id,
                )

        if settings.miner_forward_summary:
            with stats_lock:
                stats["forwards"] = int(stats["forwards"]) + 1
                stats["solve_s_total"] = float(stats["solve_s_total"]) + solve_s
                nf = int(stats["forwards"])
                tot = float(stats["solve_s_total"])
                lok = int(stats["local_ok"])
                lfail = int(stats["local_fail"])
            avg = tot / nf if nf else 0.0
            tf = f" template={template_fn}" if template_fn else ""
            lt = f" {local_tag}" if local_tag else ""
            logger.info(
                "miner_forward_summary theorem_id={} split={}{} prover_s={:.2f}s trace_chars={} proof_chars={}"
                "{} session_forwards={} session_avg_prover_s={:.2f}s session_local_ok={} session_local_fail={}",
                synapse.theorem_id,
                split,
                tf,
                solve_s,
                len(trace or ""),
                len(proof or ""),
                lt,
                nf,
                avg,
                lok,
                lfail,
            )

        if phase == "commit":
            if settings.miner_local_verify and local_lean_status != "PASS":
                return reject_synopsis(
                    synapse,
                    400,
                    "commit phase requires local Lean PASS before publishing commitment "
                    f"(status={local_lean_status})",
                )
            rblob = reasoning_blob_for_commit(trace, steps)
            nonce_b = secrets.token_bytes(32)
            pre = commit_preimage_v1(
                theorem_id=synapse.theorem_id or "",
                metronome_id=str(synapse.metronome_id or ""),
                nonce=nonce_b,
                proof_script=proof or "",
                reasoning_blob=rblob,
            )
            ch = commitment_hex_from_preimage(pre)
            cr_cache.store(cr_key, (nonce_b.hex(), proof or "", trace or "", steps))
            synapse.proof_commitment_hex = ch
            synapse.commit_reveal_phase = "commit"
            synapse.proof_script = ""
            synapse.reasoning_trace = ""
            synapse.reasoning_steps = None
            synapse.commit_reveal_nonce_hex = None
            synapse.miner_verify_attest_signature_hex = None
            err = synapse_payload_error(synapse, settings)
            if err:
                return reject_synopsis(synapse, 413, err)
            logger.info(
                "miner commit phase theorem_id={} metronome_id={} commitment_prefix={}",
                synapse.theorem_id,
                synapse.metronome_id,
                ch[:16],
            )
            return _with_computed_body_hash(synapse)

        synapse.reasoning_steps = steps
        synapse.reasoning_trace = trace
        synapse.proof_script = proof

        if settings.lemma_miner_verify_attest_enabled:
            if wallet is None or not hasattr(wallet, "hotkey"):
                logger.error("miner attest enabled but wallet not bound on axon forward")
                return reject_synopsis(synapse, 500, "miner misconfigured: wallet required for attest")
            validator_hotkey = str(getattr(getattr(synapse, "dendrite", None), "hotkey", "") or "").strip()
            if not validator_hotkey:
                return reject_synopsis(synapse, 400, "miner attest requires validator dendrite hotkey")
            if local_lean_status != "PASS":
                return reject_synopsis(
                    synapse,
                    400,
                    (
                        "LEMMA_MINER_VERIFY_ATTEST_ENABLED requires local Lean verify PASS "
                        "(set LEMMA_MINER_LOCAL_VERIFY=1)"
                    ),
                )
            msg = miner_verify_attest_message(synapse, validator_hotkey=validator_hotkey)
            synapse.miner_verify_attest_signature_hex = sign_miner_verify_attest(wallet, msg)

        err = synapse_payload_error(synapse, settings)
        if err:
            return reject_synopsis(synapse, 413, err)
        logger.info(
            "miner answered theorem_id={} metronome_id={} prover_s={:.2f}s proof_chars={} trace_chars={} "
            "local_lean={}",
            synapse.theorem_id,
            synapse.metronome_id,
            solve_s,
            len(proof or ""),
            len(trace or ""),
            local_lean_status,
        )
        return _with_computed_body_hash(synapse)

    return forward
