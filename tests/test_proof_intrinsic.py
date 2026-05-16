from lemma.scoring.proof_intrinsic import proof_intrinsic_score, strip_lean_comments_for_intrinsic


def test_proof_intrinsic_empty() -> None:
    assert proof_intrinsic_score("") == 0.0


def test_proof_intrinsic_increases_with_content() -> None:
    a = proof_intrinsic_score("theorem t : True := by trivial")
    b = proof_intrinsic_score("theorem t : True := by\n" + "  simp\n" * 20)
    assert 0.0 <= a <= 1.0
    assert 0.0 <= b <= 1.0
    assert b >= a


def test_proof_intrinsic_comment_padding_stripped_by_default() -> None:
    padded = (
        "theorem t : True := by trivial\n"
        + "-- by by by by by by by by by by\n"
        + "-- " + ("x" * 8000) + "\n"
    )
    assert proof_intrinsic_score(padded, strip_comments=True) < proof_intrinsic_score(
        padded,
        strip_comments=False,
    )


def test_proof_intrinsic_comment_only_lines_do_not_inflate_score() -> None:
    base = "theorem t : True := by\n  trivial\n"
    padded = base + ("-- by by by by by by by by by by\n\n" * 100)
    assert proof_intrinsic_score(padded, strip_comments=True) == proof_intrinsic_score(
        base,
        strip_comments=True,
    )


def test_strip_lean_comments_removes_blocks_and_lines() -> None:
    s = "/- outer /- inner -/ -/\ntheorem t : True := by trivial -- trailing"
    out = strip_lean_comments_for_intrinsic(s)
    assert "/-" not in out and "--" not in out
    assert "theorem t" in out
