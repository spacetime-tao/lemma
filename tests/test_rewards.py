from __future__ import annotations

from lemma.validator.rewards import (
    RollingScoreStore,
    apply_rolling_outcomes,
    load_rolling_scores,
    partition_same_coldkey_weights,
    rolling_effective_alpha,
    rolling_weights,
    save_rolling_scores,
)


def test_rolling_effective_alpha_scales_by_difficulty() -> None:
    easy = rolling_effective_alpha(0.08, 1.0)
    hard = rolling_effective_alpha(0.08, 4.0)

    assert hard > easy


def test_apply_rolling_outcomes_pass_and_fail() -> None:
    scores = {1: 0.5, 2: 0.5}

    apply_rolling_outcomes(scores, {1: True, 2: False}, alpha=0.1, difficulty_weight=1.0)

    assert abs(scores[1] - 0.55) < 1e-9
    assert abs(scores[2] - 0.45) < 1e-9


def test_rolling_weights_normalize_positive_scores() -> None:
    assert rolling_weights({1: 0.0, 2: 0.25, 3: 0.75}) == {2: 0.25, 3: 0.75}
    assert rolling_weights({1: 0.0}) == {}


def test_legacy_ema_file_bootstraps_rolling_scores(tmp_path) -> None:
    path = tmp_path / "scores.json"
    path.write_text('{"version": 2, "ema_by_uid": {"1": 0.4, "2": 1.2}}', encoding="utf-8")

    store = load_rolling_scores(path)

    assert store.version == 3
    assert store.rolling_score_by_uid == {1: 0.4, 2: 1.0}


def test_rolling_score_roundtrip(tmp_path) -> None:
    path = tmp_path / "scores.json"
    save_rolling_scores(path, RollingScoreStore(rolling_score_by_uid={3: 0.75}))

    assert load_rolling_scores(path).rolling_score_by_uid == {3: 0.75}


def test_same_coldkey_partition_caps_group_then_renormalizes() -> None:
    weights = partition_same_coldkey_weights(
        {1: 0.6, 2: 0.2, 3: 0.2},
        {1: "cold-a", 2: "cold-a", 3: "cold-b"},
    )

    assert weights[1] > weights[2]
    assert abs(sum(weights.values()) - 1.0) < 1e-12
    assert weights[3] > 0.2
