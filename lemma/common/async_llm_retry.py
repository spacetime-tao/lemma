"""Shared exponential backoff for transient LLM HTTP errors."""

from __future__ import annotations

import asyncio
import random
from collections.abc import Awaitable, Callable
from typing import TypeVar

from loguru import logger
from openai import APIConnectionError, APITimeoutError, InternalServerError, RateLimitError

T = TypeVar("T")

# OpenAI-compatible SDK (also used for Chutes, Gemini OpenAI shim, vLLM).
TRANSIENT_OPENAI_COMPAT: tuple[type[BaseException], ...] = (
    APIConnectionError,
    APITimeoutError,
    InternalServerError,
    RateLimitError,
)

def require_anthropic_sdk():
    try:
        import anthropic
    except ImportError as e:
        raise RuntimeError("Anthropic support requires the optional dependency: uv sync --extra anthropic") from e
    return anthropic


def anthropic_async_client_cls():
    return require_anthropic_sdk().AsyncAnthropic


def anthropic_transient_exceptions() -> tuple[type[BaseException], ...]:
    anthropic = require_anthropic_sdk()
    return (
        anthropic.APIConnectionError,
        anthropic.APITimeoutError,
        anthropic.InternalServerError,
        anthropic.RateLimitError,
    )


def fail_fast_instead_of_retry(exc: BaseException) -> bool:
    """Do not backoff-retry when the provider says billing/quota is exhausted."""
    msg = str(exc).lower()
    if "prepayment credits are depleted" in msg:
        return True
    if "payment required" in msg and "quota" in msg:
        return True
    return False


async def async_llm_retry(
    factory: Callable[[], Awaitable[T]],
    *,
    max_attempts: int,
    transient_exceptions: tuple[type[BaseException], ...],
) -> T:
    """Run async factory with exponential backoff on transient HTTP/API errors."""
    n = max(1, int(max_attempts))
    last: BaseException | None = None
    for attempt in range(n):
        try:
            return await factory()
        except transient_exceptions as e:
            if fail_fast_instead_of_retry(e):
                logger.warning("LLM error looks billing/quota-related — not retrying: {}", e)
                raise
            last = e
            if attempt >= n - 1:
                raise
            wait_s = min(90.0, 5.0 * (2**attempt))
            jitter = random.uniform(0.0, min(3.0, wait_s * 0.15))
            wait_total = wait_s + jitter
            logger.warning(
                "LLM HTTP transient error ({}) attempt {}/{} — retry in {:.1f}s: {}",
                type(e).__name__,
                attempt + 1,
                n,
                wait_total,
                e,
            )
            await asyncio.sleep(wait_total)
    if last is None:
        raise RuntimeError("async_llm_retry exhausted without capturing an exception")
    raise last
