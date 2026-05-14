from lemma.common.config import LemmaSettings
from lemma.common.synapse_limits import synapse_payload_error
from lemma.protocol import LemmaChallenge


def _challenge(**kwargs) -> LemmaChallenge:
    data = {
        "theorem_id": "known/test/one",
        "theorem_statement": "theorem t : True := by sorry",
        "lean_toolchain": "lt",
        "mathlib_rev": "mr",
        "poll_id": "poll-1",
    }
    data.update(kwargs)
    return LemmaChallenge(**data)


def test_challenge_payload_check_keeps_statement_cap() -> None:
    settings = LemmaSettings(synapse_max_statement_chars=1024)

    err = synapse_payload_error(_challenge(theorem_statement="x" * 1025), settings, response=False)

    assert err == "theorem_statement too large"


def test_challenge_payload_check_skips_response_proof_cap_on_request() -> None:
    settings = LemmaSettings(synapse_max_proof_chars=4)
    synapse = _challenge(proof_script="response field")

    assert synapse_payload_error(synapse, settings, response=False) is None
    assert synapse_payload_error(synapse, settings) == "proof_script too large"
