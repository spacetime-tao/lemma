"""Human-readable prover fingerprint for synapse export (no secrets)."""

from __future__ import annotations

from lemma.common.config import LemmaSettings


def prover_model_card_text(settings: LemmaSettings) -> str:
    """Stable short string for ``LemmaChallenge.model_card`` (training exports, analytics)."""
    prov = (settings.prover_provider or "anthropic").lower()
    if prov == "openai":
        m = settings.prover_model or settings.openai_model
        base = (settings.prover_openai_base_url_resolved() or "").strip().rstrip("/")
        if base:
            return f"prover=openai model={m} base_url={base}"[:500]
        return f"prover=openai model={m}"[:500]
    m = settings.prover_model or settings.anthropic_model
    return f"prover=anthropic model={m}"[:500]
