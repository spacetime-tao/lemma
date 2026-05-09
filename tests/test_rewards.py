"""Reward assembly from proof heuristic + judge rubric."""

from lemma.judge.base import RubricScore
from lemma.scoring.dedup import submission_fingerprint
from lemma.scoring.proof_intrinsic import proof_intrinsic_score
from lemma.scoring.rewards import entry_from_scores


def _rubric(composite: float) -> RubricScore:
    return RubricScore(coherence=composite, exploration=composite, clarity=composite, composite=composite)


def test_entry_from_scores_uses_judge_only_when_proof_weight_zero() -> None:
    trace = "short trace"
    theorem = "theorem t : True := by sorry"
    proof = "theorem t : True := by trivial"

    entry = entry_from_scores(
        7,
        _rubric(0.8),
        trace,
        theorem_statement=theorem,
        proof_script=proof,
        proof_weight=0.0,
    )

    assert entry.uid == 7
    assert entry.reasoning_score == 0.8
    assert entry.tokens == len(trace)
    assert entry.submission_fp == submission_fingerprint(theorem, proof, trace)


def test_entry_from_scores_clamps_proof_weight() -> None:
    proof = "theorem t : True := by\n  trivial\n"
    entry = entry_from_scores(
        1,
        _rubric(0.1),
        "trace",
        theorem_statement="theorem t : True := by sorry",
        proof_script=proof,
        proof_weight=2.0,
    )

    assert entry.reasoning_score == proof_intrinsic_score(proof)


def test_entry_from_scores_passes_comment_strip_setting() -> None:
    proof = (
        "theorem t : True := by trivial\n"
        + "-- by by by by by by by by by by\n"
        + "-- "
        + ("x" * 8000)
        + "\n"
    )
    stripped = entry_from_scores(
        1,
        _rubric(0.0),
        "trace",
        theorem_statement="theorem t : True := by sorry",
        proof_script=proof,
        proof_weight=1.0,
        proof_intrinsic_strip_comments=True,
    )
    unstripped = entry_from_scores(
        1,
        _rubric(0.0),
        "trace",
        theorem_statement="theorem t : True := by sorry",
        proof_script=proof,
        proof_weight=1.0,
        proof_intrinsic_strip_comments=False,
    )

    assert stripped.reasoning_score == proof_intrinsic_score(proof, strip_comments=True)
    assert unstripped.reasoning_score == proof_intrinsic_score(proof, strip_comments=False)
    assert stripped.reasoning_score < unstripped.reasoning_score
