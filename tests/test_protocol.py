"""Manual proof synapse serialization."""

from lemma.protocol import LemmaChallenge, synapse_miner_response_integrity_ok


def _challenge(**updates: object) -> LemmaChallenge:
    data = {
        "theorem_id": "known/demo",
        "theorem_statement": "import Mathlib\n\ntheorem demo : True := by\n  sorry\n",
        "imports": ["Mathlib"],
        "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
        "mathlib_rev": "5450b53e5ddc",
        "poll_id": "known/demo:1:2",
        "proof_script": (
            "import Mathlib\n\nnamespace Submission\n\n"
            "theorem demo : True := by\n  trivial\n\nend Submission\n"
        ),
    }
    data.update(updates)
    return LemmaChallenge(**data)


def test_lemma_challenge_json_roundtrip() -> None:
    s = _challenge()

    s2 = LemmaChallenge.model_validate_json(s.model_dump_json())

    assert s2.theorem_id == s.theorem_id
    assert s2.poll_id == s.poll_id
    assert s2.proof_script == s.proof_script


def test_body_hash_includes_proof() -> None:
    a = _challenge(proof_script="proof a")
    b = _challenge(proof_script="proof b")

    assert a.body_hash != b.body_hash


def test_synapse_miner_response_integrity_ok_accepts_missing_response_hash() -> None:
    assert synapse_miner_response_integrity_ok(_challenge()) is True


def test_synapse_miner_response_integrity_ok_matches_header_hash() -> None:
    s = _challenge()
    s2 = s.model_copy(update={"computed_body_hash": s.body_hash})

    assert synapse_miner_response_integrity_ok(s2) is True


def test_synapse_miner_response_integrity_ok_mismatch() -> None:
    s = _challenge()
    s2 = s.model_copy(update={"computed_body_hash": "0" * 64})

    assert synapse_miner_response_integrity_ok(s2) is False
