"""Map chain head to a stable problem seed (validator alignment).

Two modes:

- ``quantize`` (default): ``(chain_head // N) * N`` — fixed **N-block** windows (default N=100).
  Everyone at the same chain height agrees on the theorem; ``lemma status`` surfaces **time left**
  until the next window in wall-clock terms.

- ``subnet_epoch``: integer bucket ``(chain_head + netuid + 1) // (tempo + 1)`` using the
  subnet ``Tempo`` hyperparameter — matches the stride used by ``blocks_until_next_epoch``.
  **Every honest node at the same block height and same netuid gets the same seed.**

Neither mode replaces governance alignment on ``LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`` /
``LEMMA_PROBLEM_SEED_MODE``, ``LEMMA_PROBLEM_SOURCE``, and identical code/registry hashes.
"""

from __future__ import annotations

from typing import Literal

ProblemSeedMode = Literal["quantize", "subnet_epoch"]

# Rough wall-clock hint for operators (Finney-style; actual slot timing varies).
BLOCK_TIME_SEC_ESTIMATE = 12.0


def first_block_of_next_seed_window(chain_head_block: int, quantize_blocks: int) -> int:
    """Smallest block height where ``problem_sample_seed_block`` advances (start of the next N-block window)."""
    q = max(1, int(quantize_blocks))
    b = int(chain_head_block)
    return ((b // q) + 1) * q


def blocks_until_quantize_boundary(chain_head_block: int, quantize_blocks: int) -> int:
    """Blocks until the next multiple of ``quantize_blocks`` (exclusive upper boundary)."""
    b = int(chain_head_block)
    nxt = first_block_of_next_seed_window(b, quantize_blocks)
    return max(1, nxt - b)


def blocks_until_challenge_may_change(
    *,
    chain_head_block: int,
    netuid: int,
    mode: ProblemSeedMode | str,
    quantize_blocks: int,
    seed_tag: str,
    subtensor: object,
) -> tuple[int, str]:
    """Blocks until the sampling window may advance (same rules as ``resolve_problem_seed``).

    - ``subnet_epoch`` with Tempo: uses ``subtensor.blocks_until_next_epoch`` when available.
    - ``quantize`` or Tempo fallback: blocks until the next ``quantize_blocks`` boundary.

    Returns ``(blocks, label)`` where ``label`` is for diagnostics / UI hints.
    """
    mode_l = (mode or "subnet_epoch").strip().lower()
    tag_l = (seed_tag or "").strip().lower()

    if mode_l == "quantize" or tag_l == "quantize_fallback_no_tempo":
        rem = blocks_until_quantize_boundary(chain_head_block, quantize_blocks)
        return rem, "quantize_window"

    # subnet_epoch with Tempo
    bu_fn = getattr(subtensor, "blocks_until_next_epoch", None)
    if callable(bu_fn):
        try:
            bu = bu_fn(netuid)
            if bu is not None:
                return max(1, int(bu)), "subnet_epoch"
        except Exception:
            pass

    rem = blocks_until_quantize_boundary(chain_head_block, quantize_blocks)
    return rem, "quantize_estimate"


def format_blocks_eta_human(blocks: int, *, seconds_per_block: float = BLOCK_TIME_SEC_ESTIMATE) -> str:
    """Human-readable duration from a block count (approximate)."""
    sec = max(0.0, float(blocks) * float(seconds_per_block))
    if sec >= 3600.0:
        return f"~{sec / 3600.0:.1f} h"
    if sec >= 60.0:
        return f"~{sec / 60.0:.0f} min"
    return f"~{sec:.0f} s"


def format_next_theorem_countdown(
    *,
    chain_head_block: int,
    blocks_until_theorem_changes: int,
    seconds_per_block: float = BLOCK_TIME_SEC_ESTIMATE,
) -> str:
    """One user-facing line: time left until the shared theorem may change (operators tune block time in .env)."""
    b = max(0, int(blocks_until_theorem_changes))
    head = int(chain_head_block)
    next_block = head + b
    eta = format_blocks_eta_human(b, seconds_per_block=seconds_per_block)
    return (
        f"Time left on this theorem: {eta} (~{b} blocks). "
        f"Next theorem starts at block {next_block}."
    )


def explain_boundary_label(
    label: str,
    *,
    quantize_blocks: int,
) -> str:
    """Short technical note for logs (prefer :func:`format_next_theorem_countdown` in CLI)."""
    t = (label or "").strip().lower()
    if t == "subnet_epoch":
        return (
            "New-theorem cadence follows chain RPC `blocks_until_next_epoch` (subnet Tempo), "
            "not a fixed `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` window."
        )
    if t == "quantize_window":
        return f"New theorem every {quantize_blocks} blocks (`LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`)."
    return "Tempo query failed; using quantize-style spacing (see LEMMA_PROBLEM_SEED_MODE)."


def problem_sample_seed_block(chain_head_block: int, quantize_blocks: int) -> int:
    """Return ``(chain_head // q) * q`` with ``q = max(1, quantize_blocks)``."""
    q = max(1, int(quantize_blocks))
    b = int(chain_head_block)
    return (b // q) * q


def subnet_epoch_index_seed(chain_head_block: int, netuid: int, tempo: int) -> int:
    """Epoch bucket index; uses stride ``tempo + 1`` (same as ``blocks_until_next_epoch``).

    All nodes querying the same ``chain_head_block`` and ``netuid`` agree on the result.
    """
    t = max(0, int(tempo))
    stride = t + 1
    effective = int(chain_head_block) + int(netuid) + 1
    return effective // stride


def resolve_problem_seed(
    *,
    chain_head_block: int,
    netuid: int,
    mode: ProblemSeedMode,
    quantize_blocks: int,
    subtensor: object,
) -> tuple[int, str]:
    """Return ``(seed_for ProblemSource.sample, tag_for_logs)``."""
    if mode == "subnet_epoch":
        tempo_fn = getattr(subtensor, "tempo", None)
        if callable(tempo_fn):
            tempo = tempo_fn(netuid, block=chain_head_block)
        else:
            tempo = None
        if tempo is None:
            fb = problem_sample_seed_block(chain_head_block, quantize_blocks)
            return fb, "quantize_fallback_no_tempo"
        return subnet_epoch_index_seed(chain_head_block, netuid, int(tempo)), "subnet_epoch"

    return problem_sample_seed_block(chain_head_block, quantize_blocks), "quantize"
