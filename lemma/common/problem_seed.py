"""Map chain head to a stable problem seed (validator alignment)."""


def problem_sample_seed_block(chain_head_block: int, quantize_blocks: int) -> int:
    """Return ``(chain_head // q) * q`` with ``q = max(1, quantize_blocks)``.

    All validators that read a chain head in the same ``q``-block window use the
    same seed for ``ProblemSource.sample``, so they issue the same challenge.
    """
    q = max(1, int(quantize_blocks))
    b = int(chain_head_block)
    return (b // q) * q
