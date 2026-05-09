from lemma.scoring.dedup import dedup_coldkeys, dedup_identical_submissions, submission_fingerprint
from lemma.scoring.pareto import ScoredEntry


def test_submission_fingerprint_stable() -> None:
    a = submission_fingerprint("t1", "p1", "r1")
    b = submission_fingerprint("t1", "p1", "r1")
    assert a == b
    assert submission_fingerprint("t1", "p1", "r2") != a


def test_dedup_identical_keeps_best_score() -> None:
    e1 = ScoredEntry(uid=1, reasoning_score=0.5, tokens=10, submission_fp="x")
    e2 = ScoredEntry(uid=2, reasoning_score=0.9, tokens=10, submission_fp="x")
    kept, dropped = dedup_identical_submissions([e1, e2], lambda e: e.submission_fp)
    assert dropped == 1
    assert len(kept) == 1 and kept[0].uid == 2


def test_dedup_coldkey_keeps_best() -> None:
    e1 = ScoredEntry(uid=1, reasoning_score=0.4, tokens=5, submission_fp="a")
    e2 = ScoredEntry(uid=2, reasoning_score=0.8, tokens=5, submission_fp="b")
    kept, dropped = dedup_coldkeys([e1, e2], lambda _u: "same_ck")
    assert dropped == 1
    assert len(kept) == 1 and kept[0].uid == 2
