from lemma.common.problem_seed import (
    blocks_until_challenge_may_change,
    blocks_until_quantize_boundary,
    first_block_of_next_seed_window,
    format_next_theorem_countdown,
    problem_sample_seed_block,
    resolve_problem_seed,
    subnet_epoch_index_seed,
)


def test_problem_sample_seed_block_quantizes() -> None:
    assert problem_sample_seed_block(1000, 25) == 1000
    assert problem_sample_seed_block(1019, 25) == 1000
    assert problem_sample_seed_block(1025, 25) == 1025


def test_problem_sample_seed_block_identity_when_q_one() -> None:
    assert problem_sample_seed_block(1019, 1) == 1019


def test_subnet_epoch_index_seed() -> None:
    # stride = 100, effective = 5000 + 3 + 1 = 5004 -> 50
    assert subnet_epoch_index_seed(5000, 3, 99) == 50


def test_resolve_quantize_ignores_tempo() -> None:
    class _ST:
        def tempo(self, netuid: int, block: int | None = None) -> int:
            return 99

    s, tag = resolve_problem_seed(
        chain_head_block=5000,
        netuid=3,
        mode="quantize",
        quantize_blocks=25,
        subtensor=_ST(),
    )
    assert tag == "quantize"
    assert s == problem_sample_seed_block(5000, 25)


def test_resolve_subnet_epoch_uses_tempo() -> None:
    class _ST:
        def tempo(self, netuid: int, block: int | None = None) -> int:
            return 99

    s, tag = resolve_problem_seed(
        chain_head_block=5000,
        netuid=3,
        mode="subnet_epoch",
        quantize_blocks=25,
        subtensor=_ST(),
    )
    assert tag == "subnet_epoch"
    assert s == subnet_epoch_index_seed(5000, 3, 99)


def test_first_block_of_next_seed_window() -> None:
    assert first_block_of_next_seed_window(100, 100) == 200
    assert first_block_of_next_seed_window(199, 100) == 200
    assert first_block_of_next_seed_window(200, 100) == 300


def test_format_next_theorem_countdown_mentions_next_block() -> None:
    line = format_next_theorem_countdown(
        chain_head_block=150,
        blocks_until_theorem_changes=50,
        seconds_per_block=12.0,
    )
    assert "200" in line
    assert "50" in line


def test_blocks_until_quantize_boundary() -> None:
    assert blocks_until_quantize_boundary(100, 25) == 25
    assert blocks_until_quantize_boundary(125, 25) == 25


def test_blocks_until_challenge_subnet_epoch_uses_subtensor() -> None:
    class _ST:
        def tempo(self, netuid: int, block: int | None = None) -> int:
            return 99

        def blocks_until_next_epoch(self, netuid: int) -> int:
            return 14

    bl, tag = blocks_until_challenge_may_change(
        chain_head_block=5000,
        netuid=3,
        mode="subnet_epoch",
        quantize_blocks=25,
        seed_tag="subnet_epoch",
        subtensor=_ST(),
    )
    assert tag == "subnet_epoch"
    assert bl == 14


def test_blocks_until_challenge_quantize_ignores_subtensor() -> None:
    class _ST:
        def blocks_until_next_epoch(self, netuid: int) -> int:
            return 2

    bl, tag = blocks_until_challenge_may_change(
        chain_head_block=100,
        netuid=3,
        mode="quantize",
        quantize_blocks=25,
        seed_tag="quantize",
        subtensor=_ST(),
    )
    assert tag == "quantize_window"
    assert bl == 25


def test_resolve_subnet_epoch_falls_back_when_no_tempo() -> None:
    class _ST:
        def tempo(self, netuid: int, block: int | None = None) -> None:
            return None

    s, tag = resolve_problem_seed(
        chain_head_block=5000,
        netuid=3,
        mode="subnet_epoch",
        quantize_blocks=25,
        subtensor=_ST(),
    )
    assert tag == "quantize_fallback_no_tempo"
    assert s == problem_sample_seed_block(5000, 25)
