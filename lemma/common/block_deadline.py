"""Miner answer deadline: chain block height + HTTP wait = blocks_left × block_time (clamped)."""

from __future__ import annotations

from loguru import logger

from lemma.common.config import LemmaSettings
from lemma.common.problem_seed import (
    blocks_until_quantize_boundary,
    effective_chain_head_for_problem_seed,
    resolve_problem_seed,
)


def _clamp_forward_wait_s(settings: LemmaSettings, raw_s: float) -> float:
    lo = float(settings.forward_wait_min_s)
    hi = float(settings.forward_wait_max_s)
    return max(lo, min(hi, float(raw_s)))


def compute_forward_deadline_and_wait(
    *,
    settings: LemmaSettings,
    subtensor: object,
    cur_block: int,
    seed_tag: str,
    wait_scale: float = 1.0,
) -> tuple[int, float]:
    """Return ``(deadline_block, forward_http_wait_seconds)``.

    * ``deadline_block`` — first chain height where this challenge is treated as late (next epoch or quantize edge).
    * ``forward_http_wait_seconds`` — validator HTTP client timeout:
      ``blocks_until_that_edge × LEMMA_BLOCK_TIME_SEC_ESTIMATE``
      (× ``wait_scale`` when split multipliers apply), then clamped by ``LEMMA_FORWARD_WAIT_{MIN,MAX}_S``.

    There is no separate fixed wall-clock budget env var; the HTTP wait follows remaining blocks.
    """
    bt = float(settings.block_time_sec_estimate)
    cb = int(cur_block)
    tag = (seed_tag or "").strip().lower()
    ws = float(wait_scale)
    if ws < 0.01:
        ws = 1.0

    bu_fn = getattr(subtensor, "blocks_until_next_epoch", None)
    if tag == "subnet_epoch" and callable(bu_fn):
        try:
            bu = bu_fn(settings.netuid)
            if bu is not None:
                bu_i = max(1, int(bu))
                deadline = cb + bu_i
                raw = bu_i * bt * ws
                return deadline, _clamp_forward_wait_s(settings, raw)
        except Exception as e:
            logger.debug("blocks_until_next_epoch in deadline calc failed: {}", e)

    rem = blocks_until_quantize_boundary(cb, settings.problem_seed_quantize_blocks)
    deadline = cb + rem
    raw = float(rem) * bt * ws
    return deadline, _clamp_forward_wait_s(settings, raw)


def forward_wait_at_chain_head(
    *,
    settings: LemmaSettings,
    subtensor: object,
    chain_head_block: int,
    wait_scale: float = 1.0,
) -> tuple[int, str, int, float]:
    """Resolve the problem seed at ``chain_head_block`` and return forward HTTP wait (blocks × time, clamped).

    Applies ``LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS`` to match ``run_epoch``.

    Returns ``(problem_seed, seed_tag, deadline_block, forward_wait_s)`` for status/doctor output.
    """
    slack = int(settings.lemma_problem_seed_chain_head_slack_blocks or 0)
    head_eff = effective_chain_head_for_problem_seed(int(chain_head_block), slack)
    problem_seed, seed_tag = resolve_problem_seed(
        chain_head_block=head_eff,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )
    deadline_block, forward_wait_s = compute_forward_deadline_and_wait(
        settings=settings,
        subtensor=subtensor,
        cur_block=head_eff,
        seed_tag=seed_tag,
        wait_scale=wait_scale,
    )
    return problem_seed, seed_tag, deadline_block, forward_wait_s
