"""Map chain head to a stable problem seed (validator alignment).

Two modes:

- ``quantize``: ``(chain_head // N) * N`` — frequent variety; peers can still diverge at
  window boundaries if they read different chain heads.

- ``subnet_epoch``: integer bucket ``(chain_head + netuid + 1) // (tempo + 1)`` using the
  subnet ``Tempo`` hyperparameter — matches the stride used by ``blocks_until_next_epoch``.
  **Every honest node at the same block height and same netuid gets the same seed.**
  Validators whose rounds fall in the **same** bucket (between tempo boundaries) also match.

Neither mode replaces governance alignment on ``LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`` /
``LEMMA_PROBLEM_SEED_MODE``, ``LEMMA_PROBLEM_SOURCE``, and identical code/registry hashes.
"""

from __future__ import annotations

from typing import Literal

ProblemSeedMode = Literal["quantize", "subnet_epoch"]


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
