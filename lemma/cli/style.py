"""Terminal styling: color when stdout is a TTY and NO_COLOR is unset."""

from __future__ import annotations

import os
import sys

import click


def colors_enabled() -> bool:
    # https://no-color.org/ — if NO_COLOR is set (any value), disable ANSI.
    return sys.stdout.isatty() and "NO_COLOR" not in os.environ


def stylize(text: str, **kwargs: object) -> str:
    if not colors_enabled():
        return text
    return click.style(text, **kwargs)


def flush_stdio() -> None:
    """Flush streams only (safe mid-command)."""
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except (BrokenPipeError, OSError):
        pass


def finish_cli_output() -> None:
    """End-of-command: newline(s) + flush so the shell prompt never sticks to the last stderr line."""
    click.echo("")
    try:
        sys.stderr.write("\n")
        sys.stderr.flush()
    except OSError:
        pass
    flush_stdio()
