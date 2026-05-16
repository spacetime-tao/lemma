from lemma.scoring.pareto import ScoredEntry
from lemma.scoring.reputation import (
    ReputationStore,
    apply_ema_to_entries,
    apply_rolling_outcomes,
    load_reputation,
    rolling_effective_alpha,
    rolling_weights,
    save_reputation,
)


def test_apply_ema_smoothes() -> None:
    entries = [
        ScoredEntry(uid=1, score=1.0, cost=10, submission_fp=""),
    ]
    out, ema = apply_ema_to_entries(
        entries,
        alpha=0.5,
        credibility_exponent=1.0,
        prev_ema={1: 0.0},
    )
    assert abs(out[0].score - 0.5) < 1e-9
    assert abs(ema[1] - 0.5) < 1e-9


def test_apply_ema_alpha_zero_no_smoothing() -> None:
    entries = [ScoredEntry(uid=1, score=0.7, cost=3, submission_fp="")]
    out, ema = apply_ema_to_entries(
        entries,
        alpha=0.0,
        credibility_exponent=1.0,
        prev_ema={1: 0.2},
    )
    assert abs(out[0].score - 0.7) < 1e-9
    assert abs(ema[1] - 0.7) < 1e-9


def test_reputation_roundtrip(tmp_path) -> None:
    p = tmp_path / "rep.json"
    s = ReputationStore(
        ema_by_uid={0: 0.25, 3: 0.9},
        credibility_by_uid={1: 0.5},
        rolling_score_by_uid={2: 0.75},
    )
    save_reputation(p, s)
    s2 = load_reputation(p)
    assert s2.ema_by_uid[0] == 0.25
    assert s2.ema_by_uid[3] == 0.9
    assert s2.credibility_by_uid[1] == 0.5
    assert s2.rolling_score_by_uid[2] == 0.75


def test_legacy_reputation_state_bootstraps_rolling_scores(tmp_path) -> None:
    p = tmp_path / "rep.json"
    p.write_text('{"version": 2, "ema_by_uid": {"1": 0.4, "2": 1.2}}', encoding="utf-8")

    s = load_reputation(p)

    assert s.version == 3
    assert s.rolling_score_by_uid == {1: 0.4, 2: 1.0}


def test_apply_ema_credibility_multiplier() -> None:
    entries = [
        ScoredEntry(uid=2, score=1.0, cost=3, submission_fp=""),
    ]
    out, ema = apply_ema_to_entries(
        entries,
        alpha=0.0,
        credibility_exponent=2.0,
        prev_ema={},
        credibility_by_uid={2: 0.5},
    )
    assert abs(out[0].score - 0.25) < 1e-9  # 1.0 * 0.5**2
    assert abs(ema[2] - 1.0) < 1e-9


def test_apply_rolling_outcomes_pass_and_fail() -> None:
    scores = {1: 0.5, 2: 0.5}

    apply_rolling_outcomes(scores, {1: True, 2: False}, alpha=0.1, difficulty_weight=1.0)

    assert abs(scores[1] - 0.55) < 1e-9
    assert abs(scores[2] - 0.45) < 1e-9


def test_difficulty_weight_changes_rolling_impact() -> None:
    easy_alpha = rolling_effective_alpha(0.08, 1.0)
    hard_alpha = rolling_effective_alpha(0.08, 4.0)

    assert hard_alpha > easy_alpha

    easy = {1: 0.0}
    hard = {1: 0.0}
    apply_rolling_outcomes(easy, {1: True}, alpha=0.08, difficulty_weight=1.0)
    apply_rolling_outcomes(hard, {1: True}, alpha=0.08, difficulty_weight=4.0)

    assert hard[1] > easy[1]


def test_miss_uses_inverse_difficulty_weight() -> None:
    easy = {1: 0.9}
    hard = {1: 0.9}

    apply_rolling_outcomes(easy, {1: False}, alpha=0.08, difficulty_weight=1.0)
    apply_rolling_outcomes(hard, {1: False}, alpha=0.08, difficulty_weight=4.0)

    assert hard[1] > easy[1]
    assert abs(hard[1] - (0.9 * (1.0 - rolling_effective_alpha(0.08, 0.25)))) < 1e-9


def test_rolling_weights_normalize_positive_scores() -> None:
    assert rolling_weights({1: 0.0, 2: 0.25, 3: 0.75}) == {2: 0.25, 3: 0.75}


def test_single_miss_does_not_zero_existing_rolling_score() -> None:
    scores = {1: 0.9}

    apply_rolling_outcomes(scores, {1: False}, alpha=0.1, difficulty_weight=1.0)

    assert 0.0 < scores[1] < 0.9
