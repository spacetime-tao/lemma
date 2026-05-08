"""START HERE onboarding screen for `lemma` / `lemma start`."""

from __future__ import annotations

import json
import os
import shlex
import sys
from typing import NamedTuple

import click

from lemma.cli.env_paths import venv_activate_script
from lemma.cli.style import finish_cli_output, stylize


class _MenuItem(NamedTuple):
    key: str
    desc: str
    billing: str | None = None  # Shown in cyan when set (paid API / cost warning).


# Order fixed for numeric shortcuts.
_MENU: tuple[_MenuItem, ...] = (
    _MenuItem(
        "setup",
        "Guided questions — fill `.env` with network, wallets, and miner or validator settings (or both)",
    ),
    _MenuItem(
        "doctor",
        "Quick health check: Python env, config, API keys, timeouts, and (if online) current chain block",
    ),
    _MenuItem(
        "docs",
        "List guide files; open one (e.g. getting started, FAQ) with flags shown in the tip below",
    ),
    _MenuItem("glossary", "Short explanations of terms you will see in logs and docs"),
    _MenuItem("status", "What block and theorem the subnet is using right now (same problem as validators)"),
    _MenuItem("problems", "Print the live challenge (the file with `sorry` you are meant to prove)"),
    _MenuItem(
        "try-prover",
        "Prover-only on the live theorem (lighter; add `--verify` for Lean)",
        "Bills your prover API",
    ),
    _MenuItem(
        "rehearsal",
        "Scoring preview — live theorem → prover → Lean (on) → judge rubric (validators & miners)",
        "Bills prover + judge; needs Docker or host lake for verify",
    ),
    _MenuItem("miner-dry", "See how your miner would look to the network — no server, no traffic"),
    _MenuItem(
        "validator-check",
        "Before you run a validator: are chain, wallet, and Lean image in order? (READY or NOT READY)",
    ),
    _MenuItem(
        "validator-dry",
        "Print validator env from `.env` only — no scoring (for full rehearsal without weights: "
        "`lemma validator dry-run`; judge-only files: `lemma judge --trace …`)",
    ),
    _MenuItem("miner", "Start your miner so validators can send you challenges"),
    _MenuItem(
        "validator",
        "Full loop — start sets weights; dry-run skips weights (FakeJudge unless LEMMA_DRY_RUN_REAL_JUDGE=1)",
    ),
    _MenuItem("meta", "Show fingerprints of your judge and problem code (should match the rest of the subnet)"),
    _MenuItem("leaderboard", "On-chain stake and rewards — not a scoreboard for math proofs"),
    _MenuItem("configure", "Update one slice of `.env` (e.g. chain, API, port, Lean) without hand-editing"),
    _MenuItem("quit", "Exit"),
)


def _menu_keys() -> list[str]:
    return [item.key for item in _MENU]


def _looks_like_shell_step(token: str) -> bool:
    """True if the user pasted a shell command into the menu prompt by mistake."""
    raw = token.strip().lower()
    if not raw:
        return False
    shell_verbs = frozenset(
        {
            "source",
            "cd",
            "export",
            "uv",
            "sudo",
            "pip",
            "pip3",
            "python",
            "python3",
            "conda",
            "npx",
            "npm",
            "pnpm",
            "yarn",
            "git",
            "curl",
            "wget",
            "cat",
            "ls",
            "echo",
            "which",
            "open",
            "kill",
            "mkdir",
            "rm",
            "mv",
            "cp",
            "chmod",
            "activate",
        },
    )
    if raw in shell_verbs:
        return True
    if raw.startswith(("./", "../", "/", "~")):
        return True
    if raw.endswith((".sh", ".zsh", ".bash")) and "/" in raw:
        return True
    return False


def _resolve_menu_selector(token: str) -> str:
    """Map first token to menu key (1–N, command name, quit aliases)."""
    raw = token.strip().lower()
    if raw.startswith("lemma "):
        raw = raw[6:].strip()
    if not raw:
        raise click.BadParameter("empty step")
    keys = _menu_keys()
    if _looks_like_shell_step(raw):
        raise click.BadParameter(
            "this prompt is not a shell — type a step number "
            f"(1–{len(keys)}) or a command name (e.g. doctor, status). "
            "Run `source .venv/bin/activate` or `uv run lemma …` in your normal terminal.",
        )
    if raw in ("q", "quit", "exit"):
        return "quit"
    if raw.isdigit():
        n = int(raw)
        if 1 <= n <= len(keys):
            return keys[n - 1]
        raise click.BadParameter(f"expected a number from 1 to {len(keys)}")
    for k in keys:
        if raw == k.lower():
            return k
    raise click.BadParameter(
        f"expected 1–{len(keys)} or one of: {', '.join(keys)}",
    )


def _parse_docs_menu_extras(extra: list[str]) -> dict[str, object]:
    """Parse argv fragments after the menu step for `lemma docs`."""
    if not extra:
        return {}
    if extra == ["--pick"]:
        return {"pick": True, "open_slug": None}
    if extra[0] == "--open":
        if len(extra) < 2:
            raise click.UsageError(
                "`--open` needs a doc slug (e.g. faq). Example from menu: 3 --open faq",
            )
        return {"pick": False, "open_slug": extra[1]}
    raise click.UsageError(
        "After docs, use `--pick` or `--open SLUG` (see `lemma docs --help`). "
        f"Got: {' '.join(extra)}",
    )


def _parse_try_prover_menu_extras(
    extra: list[str], *, menu_assume_yes: bool, default_verify: bool = False
) -> dict[str, object]:
    """Parse argv fragments after the menu step for `lemma try-prover` / `lemma rehearsal`."""
    kwargs: dict[str, object] = {
        "assume_yes": menu_assume_yes,
        "do_verify": default_verify,
        "block": None,
        "retry_attempts": None,
        "host_lean": False,
        "docker_verify": False,
    }
    i = 0
    while i < len(extra):
        t = extra[i]
        if t == "--verify":
            kwargs["do_verify"] = True
            i += 1
        elif t == "--no-verify":
            kwargs["do_verify"] = False
            i += 1
        elif t in ("--yes", "-y"):
            kwargs["assume_yes"] = True
            i += 1
        elif t == "--block" and i + 1 < len(extra):
            kwargs["block"] = int(extra[i + 1])
            i += 2
        elif t == "--retry-attempts" and i + 1 < len(extra):
            ra = int(extra[i + 1])
            if not 1 <= ra <= 32:
                raise click.UsageError(f"--retry-attempts must be 1–32, got {ra}")
            kwargs["retry_attempts"] = ra
            i += 2
        elif t == "--host-lean":
            kwargs["host_lean"] = True
            i += 1
        elif t == "--docker-verify":
            kwargs["docker_verify"] = True
            i += 1
        else:
            raise click.UsageError(
                "After try-prover / rehearsal, optional flags: `--verify`, `--no-verify`, `--host-lean`, "
                "`--docker-verify`, `--block N`, `--retry-attempts N`, `-y`. "
                f"See `lemma try-prover --help` / `lemma rehearsal --help`. Got: {' '.join(extra)}",
            )
    if kwargs["host_lean"] and kwargs["docker_verify"]:
        raise click.UsageError("Use only one of --host-lean and --docker-verify.")
    return kwargs


_STEPS_ALLOWING_EXTRAS = frozenset({"docs", "try-prover", "rehearsal"})


def dispatch_menu_command(
    ctx: click.Context,
    group: click.Group,
    key: str,
    extra: list[str],
    *,
    menu_assume_yes_for_try_prover: bool,
) -> None:
    """Run one menu item (shared by interactive prompt and ``lemma <n>`` shorthand)."""
    if extra and key not in _STEPS_ALLOWING_EXTRAS:
        click.echo(
            stylize(
                f"Ignoring extra arguments ({' '.join(extra)}). "
                "Only steps docs, try-prover, and rehearsal accept flags here; "
                f"otherwise run e.g. `lemma {key}` with flags in your shell.",
                fg="yellow",
            ),
            err=True,
        )

    if key == "quit":
        click.echo(stylize("Bye.", dim=True))
        return

    if key == "configure":
        click.echo(
            stylize("\nlemma configure", fg="cyan", bold=True)
            + stylize(" — merge prompts into `.env` (run from repo root)\n", dim=True),
            nl=False,
        )
        subs = (
            ("chain", "NETUID, subtensor endpoint, wallet names"),
            ("axon", "AXON_PORT (miners)"),
            ("lean-image", "Write fixed LEAN_SANDBOX_IMAGE; build with scripts/prebuild_lean_image.sh first"),
            ("judge", "Validator judge LLM (Chutes / Anthropic / custom)"),
            ("prover", "Miner prover LLM (full wizard)"),
            ("prover-model", "PROVER_MODEL only (miner model id)"),
            ("prover-retries", "LEMMA_PROVER_LLM_RETRY_ATTEMPTS (gateway retries per forward)"),
            ("subnet-pins", "Write meta hash pins into `.env` (after env matches subnet policy)"),
        )
        cmd_w = max(len(f"lemma configure {n}") for n, _ in subs)
        for name, hint in subs:
            cmd = f"lemma configure {name}"
            gap = max(2, cmd_w - len(cmd) + 2)
            click.echo(f"  {stylize(cmd, fg='green')}{' ' * gap}{stylize(hint, dim=True)}")
        click.echo(
            stylize("\nSame commands: ", dim=True)
            + stylize("lemma configure --help", fg="green")
            + stylize("\n", dim=True),
            nl=False,
        )
        return

    if key == "problems":
        pg = group.get_command(ctx, "problems")
        if isinstance(pg, click.Group):
            show_cmd = pg.get_command(ctx, "show")
            if show_cmd is not None:
                ctx.invoke(show_cmd, problem_id=None, current=True, block=None)
        return

    if key == "miner":
        mg = group.get_command(ctx, "miner")
        if isinstance(mg, click.Group):
            st = mg.get_command(ctx, "start")
            if st is not None:
                ctx.invoke(st, max_forwards_per_day=None)
        return

    if key == "validator":
        vg = group.get_command(ctx, "validator")
        if isinstance(vg, click.Group):
            st = vg.get_command(ctx, "start")
            if st is not None:
                ctx.invoke(st, dry_run=False)
        return

    spec: dict[str, tuple[str, dict[str, object]]] = {
        "setup": ("setup", {}),
        "doctor": ("doctor", {}),
        "docs": ("docs", {}),
        "glossary": ("glossary", {}),
        "status": ("status", {}),
        "try-prover": ("try-prover", {"assume_yes": menu_assume_yes_for_try_prover}),
        "rehearsal": ("rehearsal", {"assume_yes": menu_assume_yes_for_try_prover}),
        "miner-dry": ("miner-dry", {}),
        "validator-check": ("validator-check", {}),
        "validator-dry": ("validator-dry", {}),
        "meta": ("meta", {}),
        "leaderboard": ("leaderboard", {}),
    }
    if key not in spec:
        return
    name, base_kwargs = spec[key]
    cmd = group.get_command(ctx, name)
    if cmd is None:
        click.echo(f"Command {name!r} not found.", err=True)
        return
    merged: dict[str, object] = dict(base_kwargs)
    if key == "docs":
        try:
            merged.update(_parse_docs_menu_extras(extra))
        except click.UsageError as e:
            click.echo(stylize(str(e), fg="red"), err=True)
            return
    elif key in ("try-prover", "rehearsal"):
        try:
            merged.update(
                _parse_try_prover_menu_extras(
                    extra,
                    menu_assume_yes=bool(base_kwargs.get("assume_yes")),
                    default_verify=(key == "rehearsal"),
                ),
            )
        except click.UsageError as e:
            click.echo(stylize(str(e), fg="red"), err=True)
            return
    ctx.invoke(cmd, **merged)


def run_quick_menu_step(ctx: click.Context, *, group: click.Group, step: int) -> None:
    """Non-interactive menu dispatch for ``lemma N`` (1-based index)."""
    keys = _menu_keys()
    if not (1 <= step <= len(keys)):
        raise click.ClickException(f"Menu step must be from 1 to {len(keys)} (got {step}).")
    key = keys[step - 1]
    raw = os.environ.pop("_LEMMA_QUICK_MENU_EXTRAS_JSON", None)
    extra: list[str] = []
    if raw:
        try:
            extra = json.loads(raw)
        except json.JSONDecodeError:
            extra = []
    if not isinstance(extra, list):
        extra = []
    extra = [str(x) for x in extra]
    click.echo(stylize(f"Menu step {step} → lemma {key}" + (f" {' '.join(extra)}" if extra else ""), dim=True))
    try:
        dispatch_menu_command(
            ctx,
            group,
            key,
            extra,
            menu_assume_yes_for_try_prover=True,
        )
    finally:
        finish_cli_output()


def show_start_here(ctx: click.Context | None = None, *, group: click.Group | None = None) -> None:
    """Print the onboarding roadmap and optionally branch into another command."""
    n_menu = len(_MENU)
    keys = _menu_keys()
    try_menu_n = keys.index("try-prover") + 1
    rehearsal_menu_n = keys.index("rehearsal") + 1
    ve = (os.environ.get("VIRTUAL_ENV") or "").strip()

    click.echo(stylize("\nlemma start — guided picks\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize("If you ", dim=True)
        + stylize("mine", fg="yellow", bold=True)
        + stylize(": ", dim=True)
        + stylize("setup", fg="green")
        + stylize(" → ", dim=True)
        + stylize("register (btcli)", fg="green")
        + stylize(" → ", dim=True)
        + stylize("miner-dry", fg="green")
        + stylize(" → ", dim=True)
        + stylize("miner", fg="green")
        + stylize("\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize("If you ", dim=True)
        + stylize("validate", fg="yellow", bold=True)
        + stylize(": ", dim=True)
        + stylize("prebuild Lean image (script)", fg="green")
        + stylize(" → ", dim=True)
        + stylize("validator-check", fg="green")
        + stylize(" → ", dim=True)
        + stylize("validator", fg="green")
        + stylize("\n", dim=True),
        nl=False,
    )

    click.echo(
        stylize("Test tools: ", dim=True)
        + stylize("lemma rehearsal", fg="green")
        + stylize(" = live theorem → prover → Lean → judge (main preview). ", dim=True)
        + stylize("try-prover", fg="green")
        + stylize(" = prover only · ", dim=True)
        + stylize("lemma judge --trace FILE", fg="green")
        + stylize(" = judge on saved text. ", dim=True)
        + stylize("validator dry-run", fg="green")
        + stylize(" = full epoch, no weights; ", dim=True)
        + stylize("FakeJudge", fg="yellow")
        + stylize(" unless LEMMA_DRY_RUN_REAL_JUDGE=1.\n", dim=True),
        nl=False,
    )

    act = venv_activate_script()
    courtesy_path = ve or (str(act) if act else "")
    if courtesy_path:
        click.echo(
            stylize("Using venv: ", dim=True)
            + stylize(courtesy_path, fg="green")
            + stylize(
                "  (`uv run lemma …` uses the same packages; `lemma env` prints `source …/activate`.)\n",
                dim=True,
            ),
            nl=False,
        )
    else:
        click.echo(
            stylize(
                "Tip: `uv sync --extra dev` then `source .venv/bin/activate` or `uv run lemma start`.\n",
                fg="yellow",
            ),
            err=True,
        )

    click.echo(
        stylize(
            f"At “Next step”, type only a number 1–{n_menu} or a command name (e.g. ",
            dim=True,
        )
        + stylize("doctor", fg="green")
        + stylize(", ", dim=True)
        + stylize(str(rehearsal_menu_n), fg="green")
        + stylize(" = rehearsal). ", dim=True)
        + stylize("Not", fg="red")
        + stylize(" a shell — no ", dim=True)
        + stylize("source", fg="yellow")
        + stylize(", ", dim=True)
        + stylize("cd", fg="yellow")
        + stylize(", ", dim=True)
        + stylize("uv", fg="yellow")
        + stylize(", or ", dim=True)
        + stylize("lemma …", fg="yellow")
        + stylize(" on that line.\n", dim=True)
        + stylize("From a normal shell: ", dim=True)
        + stylize(f"lemma {try_menu_n}", fg="green")
        + stylize(" / ", dim=True)
        + stylize(f"lemma {try_menu_n} --verify", fg="green")
        + stylize(" (prover) · ", dim=True)
        + stylize(f"lemma {rehearsal_menu_n}", fg="green")
        + stylize(" / ", dim=True)
        + stylize(f"lemma {rehearsal_menu_n} --no-verify", fg="green")
        + stylize(" (rehearsal) skip this prompt.\n", dim=True),
        nl=False,
    )

    click.echo(
        stylize("\nPick one (default ", dim=True)
        + stylize("1 = setup", fg="cyan")
        + stylize("). Ctrl+C to exit", dim=True)
        + (
            stylize(" (then `lemma env` / `uv sync` if needed).\n", dim=True)
            if ve
            else stylize(" — run `uv sync` / activate first if commands fail.\n", dim=True)
        ),
        nl=False,
    )
    max_key = max(len(item.key) for item in _MENU)
    num_width = len(str(len(_MENU)))
    click.echo(stylize("  " + "—" * min(72, 12 + max_key + num_width), dim=True))
    for i, item in enumerate(_MENU, start=1):
        num = stylize(f"{i:>{num_width}}", fg="yellow")
        name = stylize(item.key.ljust(max_key), fg="green")
        rest = item.desc
        if item.billing:
            rest = rest + "  " + stylize(item.billing, fg="blue", bold=True)
        click.echo(f"  {num}  {name}  {rest}")
    click.echo(stylize("  " + "—" * min(72, 12 + max_key + num_width), dim=True))
    click.echo(
        stylize("More: ", dim=True)
        + stylize("docs/faq.md", fg="cyan")
        + stylize(" · ", dim=True)
        + stylize("docs/getting-started.md", fg="cyan")
        + stylize("\n", dim=True),
        nl=False,
    )

    if ctx is None or group is None or not sys.stdin.isatty():
        click.echo(
            stylize("Non-interactive: use shell commands (e.g. `lemma doctor`) — menu needs a TTY.", dim=True),
        )
        return

    default_step = "1"
    try:
        raw_line = click.prompt(
            stylize("Next step", fg="cyan", bold=True),
            default=default_step,
            show_default=True,
        )
    except (click.Abort, EOFError):
        # Ctrl+C / Ctrl+D at the prompt — still hand off to a `.venv` subshell when enabled (same as after a step).
        finish_cli_output()
        from lemma.cli.interactive_venv_shell import (
            maybe_exec_venv_shell_after_interactive_menu,
        )

        maybe_exec_venv_shell_after_interactive_menu()
        return

    line_stripped = (raw_line or default_step).strip() or default_step
    try:
        parts = shlex.split(line_stripped)
    except ValueError:
        parts = line_stripped.split()
    if not parts:
        parts = [default_step]

    try:
        key = _resolve_menu_selector(parts[0])
    except click.BadParameter as e:
        click.echo(
            stylize(
                f"{e} "
                f"Use a number 1–{len(_MENU)} or a command name; optional flags only after docs / try-prover / "
                "rehearsal "
                "(e.g. `3 --open faq`). For anything else run `lemma <command>` in your shell.",
                fg="red",
            ),
            err=True,
        )
        return

    extra = parts[1:]
    try:
        dispatch_menu_command(
            ctx,
            group,
            key,
            extra,
            menu_assume_yes_for_try_prover=True,
        )
    finally:
        finish_cli_output()

    if key != "quit":
        from lemma.cli.interactive_venv_shell import (
            maybe_exec_venv_shell_after_interactive_menu,
        )

        maybe_exec_venv_shell_after_interactive_menu()
