"""START HERE onboarding screen for `lemma` / `lemma start`."""

from __future__ import annotations

import sys

import click

from lemma.cli.style import stylize

# (command_key, one-line description) — order fixed for numeric shortcuts.
_MENU: tuple[tuple[str, str], ...] = (
    ("setup", "Write .env interactively (NETUID, chain, wallets, API keys, …)"),
    ("doctor", "Sanity check: .venv, config load, optional chain RPC"),
    ("docs", "Print doc file paths (add --open on CLI to open in a desktop app)"),
    ("status", "Chain head + problem seed + theorem (same rule as validators)"),
    (
        "try-prover",
        "Run prover on current theorem (bills your LLM API — same as receiving a forward)",
    ),
    ("miner-dry", "Same as shell: lemma miner-dry or lemma miner --dry-run"),
    (
        "validator-dry",
        "Print validator env only (for repeating rounds without weights use validator --dry-run)",
    ),
    (
        "miner",
        "Run miner axon for real (listens for validators; Ctrl+C to stop)",
    ),
    (
        "validator",
        "Run validator rounds for real (Lean + judge; Ctrl+C to stop)",
    ),
    (
        "meta",
        "Fingerprints: judge stack + template registry (must match other validators)",
    ),
    ("quit", "Exit this menu"),
)


class _NextStepParam(click.ParamType):
    """Accept 1–N, command name, or quit aliases."""

    name = "step"

    def __init__(self) -> None:
        self._keys = [k for k, _ in _MENU]

    def convert(self, value: object, param: click.Parameter | None, ctx: click.Context | None) -> str:
        raw = " ".join(str(value).strip().lower().split())
        if raw.startswith("lemma "):
            raw = raw[6:].strip()
        if raw in ("q", "quit", "exit"):
            return "quit"
        if raw.isdigit():
            n = int(raw)
            if 1 <= n <= len(self._keys):
                return self._keys[n - 1]
        for k in self._keys:
            if raw == k.lower():
                return k
        raise click.BadParameter(
            f"expected 1–{len(self._keys)} or one of: {', '.join(self._keys)}",
        )


def show_start_here(ctx: click.Context | None = None, *, group: click.Group | None = None) -> None:
    """Print the onboarding roadmap and optionally branch into another command."""
    click.echo(stylize("\nLemma — START HERE\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize("Install Python deps in your normal terminal first: ", dim=True)
        + stylize("uv sync --extra dev", fg="yellow")
        + stylize("  (this prompt is not a shell)\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize("Then either ", dim=True)
        + stylize("source .venv/bin/activate", fg="yellow")
        + stylize(" and run ", dim=True)
        + stylize("lemma …", fg="green")
        + stylize(", or ", dim=True)
        + stylize("uv run lemma …", fg="yellow")
        + stylize(", or ", dim=True)
        + stylize("./scripts/lemma-run lemma …", fg="yellow")
        + stylize(".\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(
            "Shell tip: type ",
            dim=True,
        )
        + stylize("lemma", fg="green")
        + stylize(" before each command (e.g. ", dim=True)
        + stylize("lemma doctor", fg="yellow")
        + stylize(", not ", dim=True)
        + stylize("doctor", fg="yellow")
        + stylize(" alone).\n", dim=True),
        nl=False,
    )
    click.echo(stylize("Then pick a step — number or one keyword (not `lemma doctor`):\n", dim=True))
    for i, (key, blurb) in enumerate(_MENU, start=1):
        num = stylize(f"{i}", fg="yellow")
        name = stylize(key, fg="green")
        click.echo(f"  {num}  {name}  {blurb}")
    click.echo(
        stylize("\nDefaults: see docs/FAQ.md (timeouts, seeds). ", dim=True)
        + stylize("docs/GETTING_STARTED.md", fg="cyan")
        + stylize(" for the full path.\n", dim=True),
        nl=False,
    )

    if ctx is None or group is None or not sys.stdin.isatty():
        click.echo(stylize("Tip: run `lemma start` for this menu.", dim=True))
        return

    key = click.prompt(
        stylize("Next step", fg="cyan", bold=True),
        type=_NextStepParam(),
        default="1",
        show_default=True,
    )
    if key == "quit":
        click.echo(stylize("Bye.", dim=True))
        return

    spec: dict[str, tuple[str, dict[str, object]]] = {
        "setup": ("setup", {}),
        "doctor": ("doctor", {}),
        "docs": ("docs", {}),
        "status": ("status", {}),
        "try-prover": ("try-prover", {}),
        "miner-dry": ("miner-dry", {}),
        "validator-dry": ("validator-dry", {}),
        "miner": ("miner", {"dry_run": False}),
        "validator": ("validator", {}),
        "meta": ("meta", {}),
    }
    if key not in spec:
        return
    name, kwargs = spec[key]
    cmd = group.get_command(ctx, name)
    if cmd is None:
        click.echo(f"Command {name!r} not found.", err=True)
        return
    ctx.invoke(cmd, **kwargs)
