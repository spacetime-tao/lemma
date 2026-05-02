"""Format structured reasoning steps for judges and token counting."""

from __future__ import annotations

from lemma.protocol import LemmaChallenge, ReasoningStep


def format_reasoning_steps(steps: list[ReasoningStep]) -> str:
    """Turn structured steps into a single numbered document for the LLM judge."""
    lines: list[str] = []
    for i, s in enumerate(steps, start=1):
        title = (s.title or "").strip()
        head = f"Step {i}" + (f" — {title}" if title else "")
        lines.append(head)
        lines.append(s.text.strip())
        lines.append("")
    return "\n".join(lines).strip()


def effective_reasoning_text(synapse: LemmaChallenge) -> str:
    """Prefer structured steps; fall back to flat ``reasoning_trace``."""
    if synapse.reasoning_steps:
        return format_reasoning_steps(synapse.reasoning_steps)
    return synapse.reasoning_trace or ""
