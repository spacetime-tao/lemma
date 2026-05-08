"""Wrap miner-supplied text for judge prompts to reduce prompt-injection surface."""

from __future__ import annotations

# Break literal triple-backticks in miner text so fenced blocks cannot terminate early.
_FENCE_BREAK = "``\u200b`"


def sanitize_miner_fenced_block(label: str, content: str | None) -> str:
    """Return a single markdown fenced block tagged ``label`` (theorem / trace / proof).

    Miner-controlled ``content`` is escaped so `` ``` `` sequences cannot close the fence.
    """
    body = (content or "").replace("\r\n", "\n")
    body = body.replace("```", _FENCE_BREAK)
    safe_label = "".join(c if c.isalnum() or c == "_" else "_" for c in label)[:64] or "block"
    return f"```{safe_label}\n{body}\n```"
