from lemma.scoring.pareto import ScoredEntry
from lemma.scoring.reputation import ReputationStore, apply_ema_to_entries, load_reputation, save_reputation


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
    s = ReputationStore(ema_by_uid={0: 0.25, 3: 0.9}, credibility_by_uid={1: 0.5})
    save_reputation(p, s)
    s2 = load_reputation(p)
    assert s2.ema_by_uid[0] == 0.25
    assert s2.ema_by_uid[3] == 0.9
    assert s2.credibility_by_uid[1] == 0.5


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
