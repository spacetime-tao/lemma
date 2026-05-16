"""Lean verifier axiom and environment-output helpers."""

from lemma.lean.cheats import axiom_scan_ok, lake_build_environment_failed


def test_lake_build_environment_failed_detects_git_dns() -> None:
    text = "fatal: unable to access 'https://github.com/': Could not resolve host: github.com"
    assert lake_build_environment_failed(text)


def test_axiom_parse_ok() -> None:
    text = "foo depends on axioms: [propext, Classical.choice, Quot.sound]"
    ok, found = axiom_scan_ok(text)
    assert ok
    assert found == {"propext", "Classical.choice", "Quot.sound"}
