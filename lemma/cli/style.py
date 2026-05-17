"""Terminal styling: color when stdout is a TTY and NO_COLOR is unset."""

from __future__ import annotations

import io
import os
import sys
from typing import Any

import click


def colors_enabled() -> bool:
    # https://no-color.org/ — if NO_COLOR is set (any value), disable ANSI.
    if "NO_COLOR" in os.environ:
        return False
    return sys.stdout.isatty() or "FORCE_COLOR" in os.environ


def stylize(text: str, **kwargs: Any) -> str:
    if not colors_enabled():
        return text
    return click.style(text, **kwargs)


def rich_help_text(command: click.Command, ctx: click.Context) -> str | None:
    if not colors_enabled():
        return None
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
    except Exception:  # noqa: BLE001
        return None

    width = ctx.terminal_width or 100
    out = io.StringIO()
    console = Console(
        file=out,
        force_terminal=True,
        color_system="standard",
        width=max(78, min(width, 120)),
        legacy_windows=False,
    )
    usage = command.get_usage(ctx).removeprefix("Usage: ").strip()
    console.print("")
    console.print(Text("Usage: ", style="bold cyan") + Text(usage, style="bold white"))
    if command.help:
        console.print("")
        console.print(Text(command.help.strip(), style="white"))

    option_rows = [record for param in command.get_params(ctx) if (record := param.get_help_record(ctx))]
    if option_rows:
        options = Table(box=None, show_header=False, expand=True, padding=(0, 1))
        options.add_column("Option", style="green", no_wrap=True)
        options.add_column("Help", style="white")
        for opts, help_text in option_rows:
            options.add_row(opts, help_text or "")
        console.print("")
        console.print(Panel(options, title="Options", title_align="left", border_style="cyan"))

    if isinstance(command, click.Group):
        command_rows: list[tuple[str, str]] = []
        for name in command.list_commands(ctx):
            subcommand = command.get_command(ctx, name)
            if subcommand is None or subcommand.hidden:
                continue
            help_lines = (subcommand.help or "").strip().splitlines()
            help_text = subcommand.short_help or (help_lines[0] if help_lines else "")
            command_rows.append((name, help_text))
        if command_rows:
            commands = Table(box=None, show_header=False, expand=True, padding=(0, 1))
            commands.add_column("Command", style="bold cyan", no_wrap=True)
            commands.add_column("Help", style="white")
            for name, help_text in command_rows:
                commands.add_row(name, help_text)
            console.print("")
            console.print(Panel(commands, title="Commands", title_align="left", border_style="cyan"))

    return out.getvalue()


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
