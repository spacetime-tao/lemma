"""Block-aligned miner forward HTTP wait (validator client timeout from chain head)."""

from lemma.common.block_deadline import compute_forward_deadline_and_wait
from lemma.common.config import LemmaSettings


def test_subnet_epoch_path_uses_blocks_until_next_epoch() -> None:
    class _ST:
        def blocks_until_next_epoch(self, netuid: int) -> int:
            return 100

    s = LemmaSettings()
    s = s.model_copy(
        update={
            "block_time_sec_estimate": 12.0,
            "netuid": 1,
            "forward_wait_min_s": 60.0,
            "forward_wait_max_s": 86400.0,
        },
    )
    db, wait = compute_forward_deadline_and_wait(
        settings=s,
        subtensor=_ST(),
        cur_block=100,
        seed_tag="subnet_epoch",
        wait_scale=1.0,
    )
    assert db == 200
    assert wait == 100 * 12.0


def test_subnet_epoch_fallback_to_quantize() -> None:
    class _ST:
        def blocks_until_next_epoch(self, netuid: int) -> None:
            return None

    s = LemmaSettings()
    s = s.model_copy(
        update={
            "problem_seed_quantize_blocks": 25,
            "block_time_sec_estimate": 12.0,
            "forward_wait_min_s": 60.0,
            "forward_wait_max_s": 86400.0,
        },
    )
    db, wait = compute_forward_deadline_and_wait(
        settings=s,
        subtensor=_ST(),
        cur_block=100,
        seed_tag="subnet_epoch",
        wait_scale=1.0,
    )
    assert db == 125
    assert wait == 25 * 12.0


def test_wait_scale_multiplies_before_clamp() -> None:
    class _ST:
        def blocks_until_next_epoch(self, netuid: int) -> int:
            return 10

    s = LemmaSettings()
    s = s.model_copy(
        update={
            "block_time_sec_estimate": 12.0,
            "forward_wait_min_s": 60.0,
            "forward_wait_max_s": 86400.0,
        },
    )
    _, wait = compute_forward_deadline_and_wait(
        settings=s,
        subtensor=_ST(),
        cur_block=0,
        seed_tag="subnet_epoch",
        wait_scale=2.0,
    )
    assert wait == 10 * 12.0 * 2.0


def test_forward_wait_respects_clamp_max() -> None:
    class _ST:
        def blocks_until_next_epoch(self, netuid: int) -> int:
            return 10_000

    s = LemmaSettings()
    s = s.model_copy(
        update={
            "block_time_sec_estimate": 12.0,
            "forward_wait_min_s": 60.0,
            "forward_wait_max_s": 300.0,
        },
    )
    _, wait = compute_forward_deadline_and_wait(
        settings=s,
        subtensor=_ST(),
        cur_block=0,
        seed_tag="subnet_epoch",
        wait_scale=1.0,
    )
    assert wait == 300.0
