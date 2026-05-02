"""Cheat scanner."""

from lemma.lean.cheats import axiom_scan_ok, scan_submission_for_cheats


def test_scan_sorry() -> None:
    r = scan_submission_for_cheats("theorem t : True := by sorry")
    assert not r.ok


def test_scan_axiom_decl() -> None:
    r = scan_submission_for_cheats("axiom bad : False\ntheorem t : True := trivial")
    assert not r.ok


def test_axiom_parse_ok() -> None:
    text = "foo depends on axioms: [propext, Classical.choice, Quot.sound]"
    ok, found = axiom_scan_ok(text)
    assert ok
    assert found == {"propext", "Classical.choice", "Quot.sound"}
