"""Axiom / Lean output helpers."""

from lemma.lean.cheats import axiom_scan_ok, lean_driver_failed


def test_lean_driver_failed_detects_unknown_constant() -> None:
    s = "error(lean.unknownIdentifier): Unknown constant `Submission.foo`"
    assert lean_driver_failed(s)


def test_axiom_scan_ok_accepts_print_output() -> None:
    text = "depends on axioms: [propext, Quot.sound, Classical.choice]"
    ok, found = axiom_scan_ok(text)
    assert ok and found == {"propext", "Quot.sound", "Classical.choice"}


def test_axiom_scan_ok_empty_axioms_rfl() -> None:
    text = "'Submission.foo' does not depend on any axioms\n"
    ok, found = axiom_scan_ok(text)
    assert ok and found == set()
