"""Operator hints when the subnet judge HTTP call fails."""

from __future__ import annotations

import click

from lemma.cli.style import stylize
from lemma.common.config import LemmaSettings


def echo_judge_http_failure_hints(exc: BaseException, settings: LemmaSettings) -> None:
    """Print stderr hints for common judge gateway failures (401, 403, 429)."""
    raw = str(exc)
    low = raw.lower()
    status = getattr(exc, "status_code", None)
    if status is None and "error code: 401" in low:
        status = 401
    if status is None and "error code: 403" in low:
        status = 403
    if status is None and "error code: 429" in low:
        status = 429

    base = (settings.openai_base_url or "").strip()
    model = (settings.openai_model or "").strip()
    prov = (settings.judge_provider or "chutes").lower()

    if status == 401 or "401" in raw or "invalid token" in low:
        click.echo(
            stylize(
                "Hint: Judge HTTP 401 — the gateway rejected the judge key in JUDGE_OPENAI_API_KEY (preferred) "
                "or legacy OPENAI_API_KEY (wrong, expired, or for a different host). For Chutes "
                "(`OPENAI_BASE_URL=https://llm.chutes.ai/v1`), use a Chutes inference token, not a Google key. "
                "Run `lemma-cli configure judge` or edit `.env`. Judge keys are separate from PROVER_OPENAI_API_KEY "
                "and from "
                "LEMMA_LEAN_VERIFY_REMOTE_BEARER (Lean worker only).",
                dim=True,
            ),
            err=True,
        )
        return
    if status == 403:
        click.echo(
            stylize(
                "Hint: Judge HTTP 403 — model or endpoint not allowed for this key (check OPENAI_MODEL matches "
                "what your operator publishes; subnet validators pin a canonical Chutes judge).",
                dim=True,
            ),
            err=True,
        )
        return
    if status == 429 or "429" in raw or "rate" in low:
        click.echo(
            stylize(
                "Hint: Judge HTTP 429 / rate limit — backoff or raise LEMMA_JUDGE_LLM_RETRY_ATTEMPTS; Chutes can "
                "saturate under burst traffic.",
                dim=True,
            ),
            err=True,
        )
        return
    if "timeout" in low or "timed out" in low:
        click.echo(
            stylize(
                "Hint: Judge read timeout — try LEMMA_JUDGE_HTTP_TIMEOUT_S or LEMMA_LLM_HTTP_TIMEOUT_S; long "
                "rubric prompts need headroom.",
                dim=True,
            ),
            err=True,
        )
        return
    # Generic: still show where traffic went (no secrets).
    if base or model:
        click.echo(
            stylize(
                f"Hint: Judge stack is JUDGE_PROVIDER={prov!r} OPENAI_MODEL={model!r} @ {base!r} — see "
                "`lemma-cli doctor` and `lemma-cli configure judge`.",
                dim=True,
            ),
            err=True,
        )
