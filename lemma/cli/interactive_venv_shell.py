"""Optional handoff: after the interactive START HERE menu, open a shell with `.venv` active."""

from __future__ import annotations

import os
import shlex
import shutil
import sys
from pathlib import Path


def _interactive_stdio_ok() -> bool:
    if sys.stdin.isatty():
        return True
    if os.name != "posix":
        return False
    try:
        with open("/dev/tty"):
            pass
    except OSError:
        return False
    else:
        return True


def _reattach_stdio_to_controlling_tty() -> bool:
    """Point stdin/stdout/stderr at the session tty so `uv run` / IDE wrappers do not leave fd 0 as a pipe."""
    if os.name != "posix":
        return False
    try:
        tty_fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        return False
    try:
        os.dup2(tty_fd, 0)
        os.dup2(tty_fd, 1)
        os.dup2(tty_fd, 2)
    finally:
        if tty_fd > 2:
            os.close(tty_fd)
    return True


def _sync_controlling_tty_after_pty() -> None:
    """New line + SGR reset on the real tty after ``pty.spawn`` returns.

    Nested PTYs (IDE / Terminal.app + our handoff) often leave the cursor mid-line, so the next
    prompt draws on top of pasted text until the user runs ``reset`` or starts a new line.
    """
    if os.name != "posix":
        return
    try:
        with open("/dev/tty", "w", encoding="utf-8", errors="replace") as tty:
            tty.write("\r\033[0m\033[39m\033[49m\n")
            tty.flush()
    except OSError:
        pass


def _exec_invocation(shell_bin: str) -> str:
    """Shell argv tail after ``exec`` so login shells stay interactive (stdin must be a real TTY)."""
    q = shlex.quote(shell_bin)
    name = Path(shell_bin).name.lower()
    if name in ("zsh", "bash", "fish"):
        return f"{q} -i"
    return q


def maybe_exec_venv_shell_after_interactive_menu() -> None:
    """After ``finish_cli_output``, hand off to an interactive shell with ``.venv`` sourced.

    We attach stdio to ``/dev/tty`` (``uv run`` / IDE wrappers often leave fd 0 as a pipe) and
    ``exec`` a login shell — **no** Python-side :func:`pty.spawn` relay, so Cursor/VS Code
    terminals do not get a nested PTY (that breaks paste, wrapping, and the prompt).

    Fallback: if ``exec`` fails, use ``pty.spawn``. Force the PTY path with
    ``LEMMA_INTERACTIVE_VENV_USE_PTY=1``. Disable the whole handoff with
    ``LEMMA_NO_INTERACTIVE_VENV_SHELL=1``.
    """
    if os.name == "nt":
        return
    if not _interactive_stdio_ok():
        return
    raw = os.environ.get("LEMMA_NO_INTERACTIVE_VENV_SHELL", "").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return

    from lemma.cli.env_paths import venv_activate_script

    act = venv_activate_script()
    if act is None or not act.is_file():
        return

    shell_bin = os.environ.get("SHELL") or ""
    if not shell_bin or not Path(shell_bin).is_file():
        shell_bin = shutil.which("zsh") or shutil.which("bash") or shutil.which("fish") or ""
    if not shell_bin:
        return

    repo_root = act.resolve().parent.parent.parent
    try:
        os.chdir(repo_root)
    except OSError:
        return

    act_q = shlex.quote(str(act.resolve()))
    inner = f". {act_q} && exec {_exec_invocation(shell_bin)}"

    import click

    from lemma.cli.style import stylize

    click.echo(
        stylize(
            "\nOpening a subshell with `.venv` active — type `exit` to return to your previous shell.\n",
            dim=True,
        ),
        nl=True,
    )
    sys.stdout.flush()
    sys.stderr.flush()

    argv = ["/bin/sh", "-c", inner]
    force_pty = os.environ.get("LEMMA_INTERACTIVE_VENV_USE_PTY", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )

    def _run_pty_fallback() -> None:
        try:
            import pty
        except ImportError:
            return
        try:
            status = pty.spawn(argv)
        except OSError:
            return
        try:
            code = os.waitstatus_to_exitstatus(status)
        except ValueError:
            code = 1
        _sync_controlling_tty_after_pty()
        raise SystemExit(code)

    if force_pty:
        try:
            _run_pty_fallback()
        except SystemExit:
            raise
        click.echo(
            stylize(
                "PTY handoff unavailable (import or spawn failed). Run `lemma env` for `source …/activate`.\n",
                fg="red",
            ),
            err=True,
        )
        return

    _reattach_stdio_to_controlling_tty()

    try:
        os.execv("/bin/sh", ["/bin/sh", "-c", inner])
    except OSError as exec_err:
        try:
            _run_pty_fallback()
        except SystemExit:
            raise
        click.echo(
            stylize(
                f"Could not start shell with `.venv` ({exec_err}). Run `lemma env` for `source …/activate`.\n",
                fg="red",
            ),
            err=True,
        )
