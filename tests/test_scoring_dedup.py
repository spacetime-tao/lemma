from lemma.scoring.dedup import dedup_identical_submissions, partition_same_coldkey_weights, submission_fingerprint
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


def test_legacy_identical_grouping_keeps_best_score() -> None:
    e1 = ScoredEntry(uid=1, score=0.5, cost=10, submission_fp="x")
    e2 = ScoredEntry(uid=2, score=0.9, cost=10, submission_fp="x")
    kept, dropped = dedup_identical_submissions([e1, e2], lambda e: e.submission_fp)
    assert dropped == 1
    assert len(kept) == 1 and kept[0].uid == 2


def test_partition_same_coldkey_weights_caps_group_share() -> None:
    adjusted, partitioned = partition_same_coldkey_weights(
        {1: 0.5, 2: 0.25, 3: 0.25},
        lambda uid: "same_ck" if uid in {2, 3} else f"ck:{uid}",
    )

    assert partitioned == 2
    assert adjusted == {1: 2 / 3, 2: 1 / 6, 3: 1 / 6}


def test_partition_same_coldkey_weights_splits_single_operator_epoch() -> None:
    adjusted, partitioned = partition_same_coldkey_weights(
        {2: 0.2, 3: 0.2, 4: 0.2, 5: 0.2, 6: 0.2},
        lambda _uid: "same_ck",
    )

    assert partitioned == 5
    assert adjusted == {2: 0.2, 3: 0.2, 4: 0.2, 5: 0.2, 6: 0.2}
