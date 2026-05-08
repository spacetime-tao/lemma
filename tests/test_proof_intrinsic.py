from lemma.scoring.proof_intrinsic import proof_intrinsic_score


def test_proof_intrinsic_empty() -> None:
    assert proof_intrinsic_score("") == 0.0


def test_proof_intrinsic_increases_with_content() -> None:
    a = proof_intrinsic_score("theorem t : True := by trivial")
    b = proof_intrinsic_score("theorem t : True := by\n" + "  simp\n" * 20)
    assert 0.0 <= a <= 1.0
    assert 0.0 <= b <= 1.0
    assert b >= a
