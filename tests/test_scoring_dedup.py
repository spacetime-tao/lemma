from lemma.scoring.dedup import dedup_coldkeys, dedup_identical_submissions, submission_fingerprint
from lemma.scoring.pareto import ScoredEntry


def test_submission_fingerprint_stable() -> None:
    a = submission_fingerprint("t1", "p1")
    b = submission_fingerprint("t1", "p1")
    assert a == b
    assert submission_fingerprint("t1", "p2") != a
    assert submission_fingerprint("t2", "p1") != a


def test_submission_fingerprint_normalizes_comments_and_whitespace() -> None:
    theorem = "theorem t : True := by\n  trivial\n"
    proof_a = "namespace Submission\n-- copied padding\n theorem t : True := by\n  trivial\nend Submission\n"
    proof_b = "namespace Submission\n\ntheorem t : True := by trivial\n\nend Submission\n"

    assert submission_fingerprint(theorem, proof_a) == submission_fingerprint(theorem, proof_b)


def test_dedup_identical_keeps_best_score() -> None:
    e1 = ScoredEntry(uid=1, score=0.5, cost=10, submission_fp="x")
    e2 = ScoredEntry(uid=2, score=0.9, cost=10, submission_fp="x")
    kept, dropped = dedup_identical_submissions([e1, e2], lambda e: e.submission_fp)
    assert dropped == 1
    assert len(kept) == 1 and kept[0].uid == 2


def test_dedup_coldkey_keeps_best() -> None:
    e1 = ScoredEntry(uid=1, score=0.4, cost=5, submission_fp="a")
    e2 = ScoredEntry(uid=2, score=0.8, cost=5, submission_fp="b")
    kept, dropped = dedup_coldkeys([e1, e2], lambda _u: "same_ck")
    assert dropped == 1
    assert len(kept) == 1 and kept[0].uid == 2
