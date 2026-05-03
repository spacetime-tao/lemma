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


def _poke_controlling_tty() -> None:
    """Write reset + newline to the session's controlling terminal (Unix).

    Cursor/VS Code and some CI wrappers replace ``sys.stdout`` / ``sys.stderr`` so ``isatty()`` can lie;
    ``/dev/tty`` is still the real terminal the shell reads for the prompt.
    """
    if os.name != "posix":
        return
    try:
        with open("/dev/tty", "w", encoding="utf-8", errors="replace") as tty:
            if "NO_COLOR" not in os.environ:
                tty.write("\r\033[0m\033[39m\033[49m\033[?25h")
            tty.write("\n\n")
            tty.flush()
    except OSError:
        pass


def finish_cli_output() -> None:
    """End-of-command: newline(s) + flush so the shell prompt redraws reliably after mixed stdout/stderr."""
    no_color = "NO_COLOR" in os.environ
    # Stderr first: many shells attach the interactive prompt to stderr-backed styling from subprocesses
    # (zsh/bash under Cursor/VS Code integrated terminals).
    for stream in (sys.stderr, sys.stdout):
        try:
            if not no_color and stream.isatty():
                # \r — column 0 if output ended mid-line; full reset + show cursor; newline.
                stream.write("\r\033[0m\033[39m\033[49m\033[?25h\n")
            else:
                stream.write("\n")
            stream.flush()
        except (BrokenPipeError, OSError):
            pass
    # Extra trailing newline on stderr nudges some IDEs to repaint the prompt.
    try:
        if sys.stderr.isatty():
            sys.stderr.write("\n")
            sys.stderr.flush()
    except (BrokenPipeError, OSError):
        pass
    click.echo("")
    _poke_controlling_tty()
    flush_stdio()
