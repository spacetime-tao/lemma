from lemma.common.config import LemmaSettings
from lemma.common.synapse_limits import synapse_payload_error
from lemma.protocol import LemmaChallenge


def _challenge(**kwargs) -> LemmaChallenge:
    data = {
        "theorem_id": "gen/1",
        "theorem_statement": "theorem t : True := by sorry",
        "lean_toolchain": "lt",
        "mathlib_rev": "mr",
        "deadline_unix": 1,
        "deadline_block": 10,
        "metronome_id": "m1",
    }
    data.update(kwargs)
    return LemmaChallenge(**data)


def test_challenge_payload_check_keeps_statement_cap() -> None:
    settings = LemmaSettings(synapse_max_statement_chars=1024)

    err = synapse_payload_error(_challenge(theorem_statement="x" * 1025), settings, response=False)

    assert err == "theorem_statement too large"


def test_challenge_payload_check_skips_response_only_commit_fields() -> None:
    settings = LemmaSettings()
    synapse = _challenge(
        commit_reveal_phase="commit",
        proof_commitment_hex="not hex",
        proof_script="response field",
    )

    assert synapse_payload_error(synapse, settings, response=False) is None
    assert (
        synapse_payload_error(synapse, settings)
        == "proof_commitment_hex must be 64 hex chars, with optional 0x prefix"
    )
