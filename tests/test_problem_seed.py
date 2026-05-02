from lemma.common.problem_seed import problem_sample_seed_block


def test_problem_sample_seed_block_quantizes() -> None:
    assert problem_sample_seed_block(1000, 25) == 1000
    assert problem_sample_seed_block(1019, 25) == 1000
    assert problem_sample_seed_block(1025, 25) == 1025


def test_problem_sample_seed_block_identity_when_q_one() -> None:
    assert problem_sample_seed_block(1019, 1) == 1019
