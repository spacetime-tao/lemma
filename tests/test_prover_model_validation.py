"""PROVER_MODEL sanity (catch common Google AI Studio copy-paste mistakes)."""

from __future__ import annotations

import pytest
from lemma.miner.prover import _raise_if_prover_model_is_studio_client_id


def test_prover_model_rejects_gen_lang_client_id() -> None:
    with pytest.raises(ValueError, match="gemini-2.0-flash"):
        _raise_if_prover_model_is_studio_client_id("gen-lang-client-0132155996")


def test_prover_model_accepts_gemini_id() -> None:
    _raise_if_prover_model_is_studio_client_id("gemini-2.0-flash")
