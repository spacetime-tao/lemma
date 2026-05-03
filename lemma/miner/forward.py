"""Axon forward handler.

Each validator query runs the prover as soon as the synapse passes gating — no intentional delay
waiting for block/time windows (manual ``lemma try-prover`` is separate and operator-triggered).
"""

import asyncio
import threading
import time

from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.lean.verify_runner import run_lean_verify
from lemma.miner.daily_budget import allow_daily_forward
from lemma.miner.gating import MetagraphCache, metagraph_incentive_for_hotkey
from lemma.miner.limits import reject_synopsis, synapse_payload_error
from lemma.miner.model_card import prover_model_card_text
from lemma.miner.prover import Prover
from lemma.problems.factory import resolve_problem
from lemma.protocol import LemmaChallenge

_stats_lock = threading.Lock()
_stats: dict[str, float | int] = {"forwards": 0, "local_ok": 0, "local_fail": 0, "solve_s_total": 0.0}


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
):
    sem = asyncio.Semaphore(max(1, settings.miner_max_concurrent_forwards))

    async def forward(synapse: LemmaChallenge) -> LemmaChallenge:
        err = synapse_payload_error(synapse, settings)
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

        logger.info(
            "miner forward: solving theorem_id={} metronome_id={} my_uid={} my_incentive={}",
            synapse.theorem_id,
            synapse.metronome_id,
            my_uid_s,
            my_inc_s,
        )
        t0 = time.perf_counter()
        async with sem:
            trace, proof, steps = await prover.solve(synapse)
        solve_s = time.perf_counter() - t0

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
                        with _stats_lock:
                            _stats["local_ok"] = int(_stats["local_ok"]) + 1
                        logger.info(
                            "miner local verify OK theorem_id={} build_s={:.2f}",
                            synapse.theorem_id,
                            vr.build_seconds,
                        )
                    else:
                        local_tag = "local_lean=FAIL"
                        local_lean_status = "FAIL"
                        with _stats_lock:
                            _stats["local_fail"] = int(_stats["local_fail"]) + 1
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

        if settings.miner_forward_summary:
            with _stats_lock:
                _stats["forwards"] = int(_stats["forwards"]) + 1
                _stats["solve_s_total"] = float(_stats["solve_s_total"]) + solve_s
                nf = int(_stats["forwards"])
                tot = float(_stats["solve_s_total"])
                lok = int(_stats["local_ok"])
                lfail = int(_stats["local_fail"])
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

        synapse.reasoning_steps = steps
        synapse.reasoning_trace = trace
        synapse.proof_script = proof
        synapse.model_card = prover_model_card_text(settings)

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
        return synapse

    return forward


def priority_stub(synapse: LemmaChallenge) -> float:
    return 0.0
