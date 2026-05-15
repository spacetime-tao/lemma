from lemma.validator.rewards import RewardCandidate, base_reward, cadence_epoch_weights


def test_base_reward_prices_by_observed_solve_fraction() -> None:
    assert base_reward(0, 30) == 0.0
    assert abs(base_reward(1, 30) - ((1.0 - 1.0 / 30.0) ** 2)) < 1e-12
    assert base_reward(30, 30) == 0.0


def test_cadence_weights_route_unearned_budget_to_owner() -> None:
    weights = cadence_epoch_weights(
        candidates=[RewardCandidate(uid=7, commitment_block=10)],
        eligible_count=30,
        owner_burn_uid=0,
    )

    assert set(weights) == {0, 7}
    assert abs(weights[7] - ((1.0 - 1.0 / 30.0) ** 2)) < 1e-12
    assert abs(sum(weights.values()) - 1.0) < 1e-12


def test_cadence_weights_rank_and_same_block_tie() -> None:
    weights = cadence_epoch_weights(
        candidates=[
            RewardCandidate(uid=1, commitment_block=10),
            RewardCandidate(uid=2, commitment_block=10),
            RewardCandidate(uid=3, commitment_block=11),
        ],
        eligible_count=6,
        owner_burn_uid=0,
    )

    earned = (1.0 - 3.0 / 6.0) ** 2
    assert abs(weights[1] - earned * 0.4) < 1e-12
    assert abs(weights[2] - earned * 0.4) < 1e-12
    assert abs(weights[3] - earned * 0.2) < 1e-12
    assert abs(sum(weights.values()) - 1.0) < 1e-12


def test_all_solvers_means_epoch_burns() -> None:
    weights = cadence_epoch_weights(
        candidates=[RewardCandidate(uid=1, commitment_block=10), RewardCandidate(uid=2, commitment_block=11)],
        eligible_count=2,
        owner_burn_uid=0,
    )

    assert weights == {0: 1.0}
