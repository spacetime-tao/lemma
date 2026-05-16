from inspect import signature

from lemma.miner.gating import zero_miner_priority
from lemma.protocol import LemmaChallenge


def test_zero_miner_priority_has_bittensor_signature() -> None:
    sig = signature(zero_miner_priority)

    assert list(sig.parameters) == ["synapse"]
    assert sig.parameters["synapse"].annotation is LemmaChallenge
    assert sig.return_annotation is float
