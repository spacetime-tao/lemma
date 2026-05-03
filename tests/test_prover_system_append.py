"""Optional LEMMA_PROVER_SYSTEM_APPEND merged into prover system text."""

from lemma.common.config import LemmaSettings
from lemma.miner.prover import _prover_system_text


def test_append_empty_is_base_only() -> None:
    s = LemmaSettings().model_copy(update={"prover_system_append": ""})
    assert _prover_system_text(s).startswith("You are an expert Lean 4 prover")
    assert "Operator append" not in _prover_system_text(s)


def test_append_concatenates() -> None:
    s = LemmaSettings().model_copy(update={"prover_system_append": "Speak simply."})
    t = _prover_system_text(s)
    assert "Operator append" in t
    assert "Speak simply." in t
