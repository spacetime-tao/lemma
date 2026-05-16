"""Lemma CLI."""

from __future__ import annotations

import json
import re
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import replace
from pathlib import Path

import click

from lemma import __version__
from lemma.cadence import cadence_problem, cadence_window, format_eta, uid_cadence_problem
from lemma.cli.style import colors_enabled, stylize
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.problems.base import Problem
from lemma.problems.factory import get_problem_source, resolve_problem


class CommitWindowClosedError(click.ClickException):
    def __init__(self, message: str, *, current_block: int, entry: object) -> None:
        super().__init__(message)
        self.current_block = int(current_block)
        self.entry = entry


def _resolve_problem_or_click(settings: LemmaSettings, problem_id: str):
    try:
        return resolve_problem(settings, problem_id)
    except KeyError as exc:
        raise click.ClickException(f"unknown target id: {problem_id}") from exc


def _chain_outcome(result: object) -> tuple[bool, str]:
    if isinstance(result, (tuple, list)) and result:
        ok = bool(result[0])
        message = "" if len(result) < 2 or result[1] is None else str(result[1])
        return ok, message
    if isinstance(result, dict):
        raw_ok = result.get("success", result.get("ok"))
        ok = bool(result) if raw_ok is None else bool(raw_ok)
        raw_message = result.get("message", result.get("msg", result.get("error")))
        return ok, "" if raw_message is None else str(raw_message)
    if isinstance(result, bool):
        return result, "" if result else "False"
    raw_ok = getattr(result, "success", getattr(result, "ok", None))
    ok = bool(result) if raw_ok is None else bool(raw_ok)
    raw_message = getattr(result, "message", getattr(result, "error", None))
    return ok, "" if raw_message is None else str(raw_message)


def _active_problem_or_click(settings: LemmaSettings, current_block: int | None = None, uid: int | None = None):
    src = get_problem_source(settings)
    try:
        block = current_block
        if block is None:
            block, _chain_error = _current_block_or_none(settings)
        seed = cadence_window(int(block or 0), settings.cadence_window_blocks).seed
        anchor = cadence_problem(src, seed)
        if uid is None:
            return anchor
        return uid_cadence_problem(
            src,
            anchor,
            seed=seed,
            uid=uid,
            variants_enabled=bool(settings.lemma_uid_variant_problems),
        )
    except ValueError as exc:
        raise click.ClickException("All known theorem targets are solved.") from exc


def _target_summary(problem: Problem | None) -> str:
    if problem is None:
        return "none"
    title = str(problem.extra.get("title") or problem.theorem_name)
    return f"{problem.id} - {title}"


def _echo_theorem_window(settings: LemmaSettings) -> None:
    source = get_problem_source(settings)
    current_block, _chain_error = _current_block_or_none(settings)
    window = cadence_window(int(current_block or 0), settings.cadence_window_blocks)
    previous = cadence_problem(source, max(0, window.seed - window.window_blocks))
    current = cadence_problem(source, window.seed)
    next_problem = cadence_problem(source, window.seed + window.window_blocks)
    click.echo(stylize("Theorem window", fg="cyan", bold=True))
    for label, problem, color in (
        ("previous theorem", previous, "yellow"),
        ("current theorem", current, "green"),
        ("next theorem", next_problem, "cyan"),
    ):
        text = _target_summary(problem)
        click.echo(stylize(f"{label:<17}", dim=True) + stylize(text, fg=color, bold=problem is not None))


def _start_miner(settings: LemmaSettings) -> None:
    from lemma.miner.service import MinerService

    setup_logging(settings.log_level)
    MinerService(settings).run()


def _kv(label: str, value: object, *, fg: str = "green") -> str:
    return stylize(f"{label:<10}", dim=True) + stylize(str(value), fg=fg, bold=True)


def _cmd(text: str) -> str:
    return stylize(text, fg="bright_blue", bold=True)


def _wallet_names(settings: LemmaSettings, role: str) -> tuple[str, str]:
    if role == "validator":
        return settings.validator_wallet_names()
    return settings.wallet_cold, settings.wallet_hot


def _settings_with_wallet_options(
    settings: LemmaSettings,
    *,
    role: str,
    wallet: str | None,
    hotkey: str | None,
) -> LemmaSettings:
    if wallet is None and hotkey is None:
        return settings
    cold, hot = _wallet_names(settings, role)
    if role == "validator":
        return settings.model_copy(
            update={
                "validator_wallet_cold": wallet or cold,
                "validator_wallet_hot": hotkey or hot,
            },
        )
    return settings.model_copy(update={"wallet_cold": wallet or cold, "wallet_hot": hotkey or hot})


def _wallet_env_updates(*, role: str, wallet: str | None, hotkey: str | None) -> dict[str, str]:
    updates: dict[str, str] = {}
    prefix = "BT_VALIDATOR_WALLET" if role == "validator" else "BT_WALLET"
    if wallet:
        updates[f"{prefix}_COLD"] = wallet
    if hotkey:
        updates[f"{prefix}_HOT"] = hotkey
    return updates


def _poll_eta(settings: LemmaSettings) -> str:
    minutes = max(1, round(float(settings.validator_poll_interval_s) / 60))
    return f"validators poll about every {minutes} min, then run Lean"


def _env_updates_for_setup(settings: LemmaSettings, role: str, current_block: int | None) -> dict[str, str]:
    from lemma.problems.known_theorems import known_theorems_manifest_sha256
    from lemma.validator.profile import validator_profile_sha256

    updates: dict[str, str] = {}
    effective = settings
    if role == "validator" and not (settings.known_theorems_manifest_expected_sha256 or "").strip():
        updates["LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED"] = known_theorems_manifest_sha256(
            settings.known_theorems_manifest_path,
        )
    if role == "validator" and not (settings.validator_profile_expected_sha256 or "").strip():
        updates["LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED"] = validator_profile_sha256(effective)
    if role == "miner":
        if settings.prover_api_key and not _env_file_has_key(Path(".env"), "LEMMA_PROVER_API_KEY"):
            updates["LEMMA_PROVER_API_KEY"] = settings.prover_api_key
        if settings.prover_base_url and not _env_file_has_key(Path(".env"), "LEMMA_PROVER_BASE_URL"):
            updates["LEMMA_PROVER_BASE_URL"] = settings.prover_base_url
        if settings.prover_model and not _env_file_has_key(Path(".env"), "LEMMA_PROVER_MODEL"):
            updates["LEMMA_PROVER_MODEL"] = settings.prover_model
    return updates


def _env_file_has_key(path: Path, key: str) -> bool:
    if not path.exists():
        return False
    prefix = f"{key}="
    return any(line.strip().startswith(prefix) for line in path.read_text(encoding="utf-8").splitlines())


def _next_command_after_setup(settings: LemmaSettings) -> str:
    from lemma.submissions import pending_submission_for_problem

    try:
        problem = _active_problem_or_click(settings)
        pending = pending_submission_for_problem(settings.miner_submissions_path, problem)
    except Exception:  # noqa: BLE001
        return "lemma status"
    if pending is None:
        return "lemma mine"
    if not pending.proof_nonce:
        return "lemma mine --replace"
    if pending.commitment_status != "committed":
        return "lemma mine --retry-commit"
    return "lemma mine"


def _settings_with_env_updates(settings: LemmaSettings, updates: dict[str, str]) -> LemmaSettings:
    model_updates: dict[str, object] = {}
    if "LEMMA_TARGET_GENESIS_BLOCK" in updates:
        model_updates["target_genesis_block"] = int(updates["LEMMA_TARGET_GENESIS_BLOCK"])
    if "LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED" in updates:
        model_updates["known_theorems_manifest_expected_sha256"] = updates[
            "LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED"
        ]
    if "LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED" in updates:
        model_updates["validator_profile_expected_sha256"] = updates["LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED"]
    if "BT_WALLET_COLD" in updates:
        model_updates["wallet_cold"] = updates["BT_WALLET_COLD"]
    if "BT_WALLET_HOT" in updates:
        model_updates["wallet_hot"] = updates["BT_WALLET_HOT"]
    if "BT_VALIDATOR_WALLET_COLD" in updates:
        model_updates["validator_wallet_cold"] = updates["BT_VALIDATOR_WALLET_COLD"]
    if "BT_VALIDATOR_WALLET_HOT" in updates:
        model_updates["validator_wallet_hot"] = updates["BT_VALIDATOR_WALLET_HOT"]
    if "LEMMA_PROVER_API_KEY" in updates:
        model_updates["prover_api_key"] = updates["LEMMA_PROVER_API_KEY"]
    if "LEMMA_PROVER_BASE_URL" in updates:
        model_updates["prover_base_url"] = updates["LEMMA_PROVER_BASE_URL"]
    if "LEMMA_PROVER_MODEL" in updates:
        model_updates["prover_model"] = updates["LEMMA_PROVER_MODEL"]
    return settings.model_copy(update=model_updates) if model_updates else settings


def _display_env_value(key: str, value: str) -> str:
    if key != "LEMMA_PROVER_API_KEY":
        return value
    if len(value) <= 10:
        return "***"
    return value[:7] + "..." + value[-4:]


def _auto_retry_commit_after_setup(settings: LemmaSettings) -> bool:
    from lemma.submissions import pending_submission_for_problem

    try:
        problem = _active_problem_or_click(settings)
    except click.ClickException:
        return False
    pending = pending_submission_for_problem(settings.miner_submissions_path, problem)
    if pending is None or not pending.proof_nonce or pending.commitment_status == "committed":
        return False

    click.echo("")
    click.echo(stylize("Stored proof found. Publishing commitment now.", fg="cyan", bold=True))
    try:
        _publish_pending_commitment(settings, problem, pending)
        miner_settings = settings
    except CommitWindowClosedError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(stylize("Commitment published. Starting miner.", fg="green", bold=True))
    _start_miner(miner_settings)
    return True


def _write_env_updates(path: Path, updates: dict[str, str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    keys = set(updates)
    out: list[str] = []
    seen: set[str] = set()
    for line in lines:
        key = line.split("=", 1)[0].strip()
        if key in keys and not line.lstrip().startswith("#"):
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    if updates:
        if out and out[-1].strip():
            out.append("")
        out.extend(f"{key}={value}" for key, value in updates.items() if key not in seen)
    path.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")


def _print_btcli_commands(settings: LemmaSettings, role: str) -> None:
    wallet_cold, wallet_hot = _wallet_names(settings, role)
    network = settings.subtensor_network or "finney"
    click.echo(stylize("btcli commands", fg="cyan", bold=True))
    click.echo(_cmd("uv sync --extra btcli"))
    click.echo(_cmd(f"btcli wallet create --wallet.name {wallet_cold} --wallet.hotkey {wallet_hot}"))
    click.echo(_cmd(f"btcli subnets show --netuid {settings.netuid} --network {network}"))
    click.echo(
        _cmd(
            f"btcli subnets register --netuid {settings.netuid} "
            f"--wallet.name {wallet_cold} --wallet.hotkey {wallet_hot} --network {network}",
        ),
    )


def _print_suggested_env(updates: dict[str, str]) -> None:
    click.echo("")
    click.echo(stylize("Suggested .env values", fg="cyan", bold=True))
    for key, value in updates.items():
        display_value = _display_env_value(key, value)
        click.echo(stylize(key, fg="bright_blue", bold=True) + "=" + stylize(display_value, fg="green"))


def _mine_preflight(settings: LemmaSettings) -> LemmaSettings:
    click.echo(stylize("Preflight", fg="cyan", bold=True))
    click.echo(_kv("wallet", f"{settings.wallet_cold}/{settings.wallet_hot}", fg="green"))

    current_block, chain_error = _current_block_or_none(settings)
    if current_block is None:
        click.echo(_kv("chain", "unavailable", fg="yellow"))
        if chain_error:
            click.echo(stylize("       " + chain_error[:160], dim=True))
    else:
        click.echo(_kv("block", current_block, fg="cyan"))

    hotkey = _wallet_hotkey_address(settings, "miner")
    click.echo(_kv("hotkey", hotkey or "unavailable", fg="green" if hotkey else "yellow"))
    registration = _registration_text(settings, hotkey)
    click.echo(_kv("subnet", registration, fg="green" if registration.startswith("registered") else "yellow"))

    needs_btcli = shutil.which("btcli") is None or hotkey is None or not registration.startswith("registered")
    if needs_btcli:
        _print_btcli_commands(settings, "miner")
    if shutil.which("docker") is None:
        click.echo(stylize("docker missing", fg="yellow", bold=True))
    if all((settings.prover_base_url, settings.prover_api_key, settings.prover_model)):
        click.echo(_kv("prover", settings.prover_model, fg="green"))
    else:
        click.echo(_kv("prover", "required unless --submission is used", fg="yellow"))
    click.echo(_kv("cadence", f"{settings.cadence_window_blocks} blocks", fg="cyan"))

    updates = _env_updates_for_setup(settings, "miner", current_block)
    if not updates:
        return settings

    _print_suggested_env(updates)
    if click.confirm("Write these setup values to .env now?", default=True):
        _write_env_updates(Path(".env"), updates)
        click.echo(stylize("Updated .env", fg="green", bold=True))
        return _settings_with_env_updates(settings, updates)
    click.echo(stylize("Continuing without .env changes.", fg="yellow"))
    return settings


def _require_prover_settings(settings: LemmaSettings) -> None:
    missing = [
        key
        for key, value in (
            ("LEMMA_PROVER_BASE_URL", settings.prover_base_url),
            ("LEMMA_PROVER_API_KEY", settings.prover_api_key),
            ("LEMMA_PROVER_MODEL", settings.prover_model),
        )
        if not (value or "").strip()
    ]
    if missing:
        raise click.ClickException(
            "Missing prover config for `lemma mine`: "
            + ", ".join(missing)
            + ". Advanced/manual override: pass --submission path/to/Submission.lean.",
        )


def _prove_with_openai_compatible_chat(settings: LemmaSettings, problem: Problem) -> str:
    base_url = str(settings.prover_base_url or "").rstrip("/")
    url = base_url + "/chat/completions"
    click.echo(stylize("Calling prover for complete Submission.lean.", fg="cyan", bold=True))
    payload = {
        "model": settings.prover_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You write Lean 4 proofs. Return only a complete Submission.lean file. "
                    "Do not include markdown fences or explanation."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Fill this Lean file so it verifies. Keep the namespace and theorem statement unchanged.\n\n"
                    + problem.submission_stub()
                ),
            },
        ],
        "temperature": 0,
        "max_tokens": int(settings.prover_max_tokens),
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings.prover_api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise click.ClickException(f"prover request failed: HTTP {exc.code} {detail}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise click.ClickException(f"prover request failed: {exc}") from exc
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise click.ClickException("prover response did not contain choices[0].message.content") from exc
    proof = _extract_submission_lean(str(content))
    click.echo(stylize("Prover returned Submission.lean; checking with Lean.", fg="green", bold=True))
    return proof


def _extract_submission_lean(text: str) -> str:
    match = re.search(r"```(?:lean|lean4)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    proof = match.group(1) if match else text
    return proof.strip() + "\n"


@click.group(name="lemma", invoke_without_command=True, context_settings={"max_content_width": 100})
@click.pass_context
@click.version_option(version=__version__)
def main(ctx: click.Context) -> None:
    """Guided Lean proof mining."""
    if ctx.invoked_subcommand is not None:
        return
    click.echo(stylize("Lemma ", fg="cyan", bold=True) + stylize(__version__, dim=True))
    click.echo("Work offline. Commit online. Lean decides whether a proof verifies.\n")
    click.echo(stylize("Commands", fg="cyan", bold=True))
    click.echo("  " + _cmd("mine") + stylize("      Verify a proof, commit it, and start the miner", dim=True))
    click.echo("  " + _cmd("status") + stylize("    Show target, phase, proof, wallet, and next step", dim=True))
    click.echo("  " + _cmd("validate") + stylize("  Check setup, then start the validator", dim=True))
    click.echo("")
    click.echo(stylize("Helper", fg="cyan", bold=True))
    click.echo("  " + _cmd("setup") + stylize("     Preflight config, wallets, registration, pins, and .env", dim=True))
    click.echo("")
    click.echo(stylize("Advanced/script commands stay callable but are hidden from the normal surface.", fg="yellow"))


@main.command("setup", help="Preflight config, wallets, registration, pins, and .env.")
@click.option("--role", type=click.Choice(["miner", "validator"]), help="Setup role.")
@click.option("--wallet", "wallet_cold", help="Coldkey/wallet name to use for this role.")
@click.option("--hotkey", "wallet_hot", help="Hotkey name to use for this role.")
def setup_cmd(role: str | None, wallet_cold: str | None, wallet_hot: str | None) -> None:
    from lemma.problems.known_theorems import known_theorems_manifest_sha256
    from lemma.validator.profile import validator_profile_sha256

    base_settings = LemmaSettings()
    role = role or click.prompt("Role", type=click.Choice(["miner", "validator"]), default="miner")
    settings = _settings_with_wallet_options(base_settings, role=role, wallet=wallet_cold, hotkey=wallet_hot)
    display_wallet_cold, display_wallet_hot = _wallet_names(settings, role)
    click.echo(stylize("Lemma setup", fg="cyan", bold=True))
    click.echo(_kv("role", role, fg="magenta"))
    click.echo(_kv("chain", f"netuid={settings.netuid} network={settings.subtensor_network}", fg="cyan"))
    click.echo(_kv("wallet", f"{display_wallet_cold}/{display_wallet_hot}", fg="green"))

    current_block, chain_error = _current_block_or_none(settings)
    if current_block is None:
        click.echo(_kv("chain", "unavailable", fg="yellow"))
        if chain_error:
            click.echo(stylize("       " + chain_error[:160], dim=True))
    else:
        click.echo(_kv("block", current_block, fg="cyan"))

    hotkey = _wallet_hotkey_address(settings, role)
    click.echo(_kv("hotkey", hotkey or "unavailable", fg="green" if hotkey else "yellow"))
    registration = _registration_text(settings, hotkey)
    click.echo(_kv("subnet", registration, fg="green" if registration.startswith("registered") else "yellow"))

    if shutil.which("btcli") is None:
        click.echo(stylize("btcli  missing", fg="yellow", bold=True))
        _print_btcli_commands(settings, role)
    else:
        click.echo(_kv("btcli", "found", fg="green"))

    if shutil.which("docker") is None:
        click.echo(stylize("docker missing", fg="yellow", bold=True))
    else:
        click.echo(_kv("docker", "found", fg="green"))

    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    click.echo(_kv("manifest", manifest_sha, fg="blue"))
    click.echo(_kv("profile", validator_profile_sha256(settings), fg="blue"))
    click.echo(_kv("cadence", f"{settings.cadence_window_blocks} blocks", fg="cyan"))

    updates = _wallet_env_updates(role=role, wallet=wallet_cold, hotkey=wallet_hot)
    updates.update(_env_updates_for_setup(settings, role, current_block))
    if not updates:
        if role == "miner" and _auto_retry_commit_after_setup(settings):
            return
        click.echo(stylize("No .env changes suggested.", fg="green", bold=True))
        return
    _print_suggested_env(updates)
    wrote_env = False
    if click.confirm("Write these values to .env?", default=False):
        _write_env_updates(Path(".env"), updates)
        click.echo(stylize("Updated .env", fg="green", bold=True))
        wrote_env = True
    else:
        click.echo(stylize("No .env changes written.", fg="yellow"))

    effective_settings = _settings_with_env_updates(settings, updates) if wrote_env else settings
    if role == "miner" and wrote_env and _auto_retry_commit_after_setup(effective_settings):
        return

    next_command = _next_command_after_setup(effective_settings)
    click.echo("")
    click.echo(stylize("Next: ", fg="cyan", bold=True) + _cmd(next_command))


@main.command("mine", help="Solve the active target.")
@click.option("--bounty", "bounty_id", help="Verify and package a Formal Conjectures bounty proof.")
@click.option("--retry-commit", is_flag=True, help="Retry the chain commitment for a stored proof.")
@click.option("--replace", "replace_stored", is_flag=True, help="Replace a stale stored proof.")
@click.option("--editor", is_flag=True, help="Open an editor instead of paste mode.")
@click.option("--wallet", "wallet_cold", help="Coldkey/wallet name for the miner.")
@click.option("--hotkey", "wallet_hot", help="Hotkey name for the miner.")
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="Use an existing Submission.lean file.",
)
@click.option("--host-lean", is_flag=True, help="Run local verification with host lake.")
def mine_cmd(
    bounty_id: str | None,
    retry_commit: bool,
    replace_stored: bool,
    editor: bool,
    wallet_cold: str | None,
    wallet_hot: str | None,
    submission_path: Path | None,
    host_lean: bool,
) -> None:
    from lemma.cli.problem_views import echo_challenge_separator, echo_lean_source, echo_problem_card
    from lemma.submissions import pending_submission_for_problem

    if bounty_id is not None:
        _mine_bounty(bounty_id, submission_path=submission_path, host_lean=host_lean)
        return
    if editor and submission_path is not None:
        raise click.ClickException("Use either --editor or --submission, not both.")
    if editor:
        raise click.ClickException("Manual cadence proof work uses --submission path/to/Submission.lean.")
    settings = _settings_with_wallet_options(LemmaSettings(), role="miner", wallet=wallet_cold, hotkey=wallet_hot)
    settings = _mine_preflight(settings)
    current_block, _chain_error = _current_block_or_none(settings)
    problem = _active_problem_or_click(settings, current_block, _miner_uid_or_none(settings))

    click.echo(stylize("Lemma mine", fg="cyan", bold=True))
    echo_problem_card(problem, heading="Active theorem")
    echo_challenge_separator()
    echo_lean_source(problem.challenge_source())
    click.echo("")

    pending = pending_submission_for_problem(settings.miner_submissions_path, problem)
    if retry_commit:
        if pending is None:
            raise click.ClickException("No stored proof for the active target yet. Run `lemma mine` first.")
        if not pending.proof_nonce:
            raise click.ClickException("Stored proof is from an older format. Run `lemma mine --replace`.")
        pending = _publish_pending_commitment(settings, problem, pending)
        click.echo(stylize("Commitment published. Starting miner.", fg="green", bold=True))
        _start_miner(settings)
        return
    if pending is not None and pending.commitment_status == "committed":
        click.echo(stylize("You already have a committed proof for this target.", fg="green", bold=True))
        click.echo("Starting miner so validators can poll it after reveal opens.")
        _start_miner(settings)
        return
    if pending is not None and not replace_stored:
        if pending.proof_nonce and pending.commitment_status not in {"commit_window_closed"}:
            raise click.ClickException("Stored proof is not committed yet. Run `lemma mine --retry-commit`.")
        raise click.ClickException("Stored proof cannot be committed as-is. Run `lemma mine --replace`.")
    if pending is not None:
        click.echo(stylize("Replacing the stored proof for this target.", fg="yellow", bold=True))

    if submission_path is not None:
        proof_script = submission_path.read_text(encoding="utf-8")
    else:
        _require_prover_settings(settings)
        proof_script = _prove_with_openai_compatible_chat(settings, problem)
    if not proof_script.strip():
        click.echo(stylize("No proof submitted. The proof was empty.", fg="yellow"))
        return

    _entry, miner_settings = _submit_proof(
        settings,
        problem_id=problem.id,
        proof_script=proof_script,
        do_verify=True,
        host_lean=host_lean,
        concise=True,
        show_next=False,
        publish_commit=True,
    )
    click.echo("")
    click.echo(stylize("Starting miner now.", fg="green", bold=True))
    click.echo(
        "Keep this running until your UID appears on "
        + stylize(miner_settings.public_dashboard_url, fg="bright_blue", bold=True)
        + stylize(" or in ", fg="cyan")
        + _cmd("lemma target ledger")
        + stylize(" if you have the validator/operator ledger locally.", fg="cyan"),
    )
    _start_miner(miner_settings)


def _mine_bounty(bounty_id: str, *, submission_path: Path | None, host_lean: bool) -> None:
    import bittensor as bt

    from lemma.formal_campaigns import (
        bounty_signature_message,
        build_bounty_package,
        campaign_by_id,
        proof_declares_campaign_theorem,
        write_bounty_package,
    )
    from lemma.lean.verify_runner import run_lean_verify

    if submission_path is None:
        raise click.ClickException("Bounty mode requires --submission path/to/Submission.lean.")
    settings = LemmaSettings()
    try:
        campaign = campaign_by_id(bounty_id, settings.formal_campaign_registry_path)
    except KeyError as exc:
        raise click.ClickException(f"unknown bounty campaign: {bounty_id}") from exc
    if campaign.status != "open":
        raise click.ClickException(f"bounty campaign is not open: {campaign.status}")
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException("Host Lean is disabled. Set LEMMA_ALLOW_HOST_LEAN=1 or omit --host-lean.")

    proof_script = submission_path.read_text(encoding="utf-8")
    if not proof_declares_campaign_theorem(campaign, proof_script):
        raise click.ClickException(f"submission must declare theorem {campaign.declaration.rsplit('.', 1)[-1]}")
    problem = campaign.to_problem()
    eff = settings.model_copy(update={"lean_use_docker": not host_lean and settings.lean_use_docker})
    click.echo(stylize("Lemma bounty", fg="cyan", bold=True))
    click.echo(stylize(campaign.title, fg="green", bold=True))
    click.echo(stylize(f"reward={campaign.reward_label}", fg="yellow", bold=True))
    click.echo(stylize("Checking proof with Lean...", fg="cyan"))
    vr = run_lean_verify(
        eff,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=problem,
        proof_script=proof_script,
    )
    if not vr.passed:
        raise click.ClickException(f"Lean rejected this bounty proof: {vr.reason}\n{vr.stderr_tail}")

    wallet = bt.Wallet(name=settings.wallet_cold, hotkey=settings.wallet_hot)
    proof_hash = build_bounty_package(
        campaign=campaign,
        proof_script=proof_script,
        solver_hotkey=wallet.hotkey.ss58_address,
        signature_hex="",
        verify_reason=vr.reason,
        build_seconds=vr.build_seconds,
    )["proof"]["proof_sha256"]
    signature = wallet.hotkey.sign(bounty_signature_message(campaign, proof_hash)).hex()
    package = build_bounty_package(
        campaign=campaign,
        proof_script=proof_script,
        solver_hotkey=wallet.hotkey.ss58_address,
        signature_hex=signature,
        verify_reason=vr.reason,
        build_seconds=vr.build_seconds,
    )
    path = write_bounty_package(settings.bounty_package_dir, package)
    click.echo(stylize("Lean accepted this bounty proof. Package written.", fg="green", bold=True))
    click.echo(f"campaign_id={campaign.id}")
    click.echo(f"solver_hotkey={wallet.hotkey.ss58_address}")
    click.echo(f"proof_sha256={proof_hash}")
    click.echo(f"package={path}")


@main.command("bounty-accept", hidden=True)
@click.option(
    "--package",
    "package_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--solver-uid", type=int, help="Optional registered subnet UID for the solver.")
@click.option("--host-lean", is_flag=True, help="Run local verification with host lake.")
def bounty_accept_cmd(package_path: Path, solver_uid: int | None, host_lean: bool) -> None:
    import json

    from bittensor_wallet import Keypair

    from lemma.formal_campaigns import (
        append_campaign_acceptance,
        bounty_signature_message,
        campaign_by_id,
        new_campaign_acceptance,
        proof_sha256,
    )
    from lemma.lean.verify_runner import run_lean_verify

    settings = LemmaSettings()
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException("Host Lean is disabled. Set LEMMA_ALLOW_HOST_LEAN=1 or omit --host-lean.")
    package = json.loads(package_path.read_text(encoding="utf-8"))
    if package.get("schema") != "lemma_bounty_proof_package_v1":
        raise click.ClickException("package schema is not lemma_bounty_proof_package_v1")
    campaign_id = str(package.get("campaign", {}).get("id") or "").strip()
    try:
        campaign = campaign_by_id(campaign_id, settings.formal_campaign_registry_path)
    except KeyError as exc:
        raise click.ClickException(f"unknown bounty campaign: {campaign_id}") from exc
    if campaign.status != "open":
        raise click.ClickException(f"bounty campaign is not open: {campaign.status}")

    proof = str(package.get("proof", {}).get("proof_script") or "")
    proof_hash = proof_sha256(proof)
    if proof_hash != str(package.get("proof", {}).get("proof_sha256") or ""):
        raise click.ClickException("package proof hash does not match proof_script")
    hotkey = str(package.get("solver", {}).get("hotkey") or "").strip()
    signature_hex = str(package.get("solver", {}).get("signature") or "").strip()
    message = bounty_signature_message(campaign, proof_hash)
    if str(package.get("solver", {}).get("signature_message") or "") != message.decode("utf-8"):
        raise click.ClickException("package signature message does not match campaign and proof")
    try:
        valid_signature = Keypair(ss58_address=hotkey).verify(message, bytes.fromhex(signature_hex))
    except Exception as exc:  # noqa: BLE001
        raise click.ClickException(f"invalid solver signature: {exc}") from exc
    if not valid_signature:
        raise click.ClickException("solver signature verification failed")

    eff = settings.model_copy(update={"lean_use_docker": not host_lean and settings.lean_use_docker})
    vr = run_lean_verify(
        eff,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=campaign.to_problem(),
        proof_script=proof,
    )
    if not vr.passed:
        raise click.ClickException(f"Lean rejected this bounty proof: {vr.reason}\n{vr.stderr_tail}")
    acceptance = new_campaign_acceptance(
        campaign_id=campaign.id,
        solver_hotkey=hotkey,
        solver_uid=solver_uid,
        proof_sha256=proof_hash,
    )
    try:
        append_campaign_acceptance(settings.campaign_acceptance_ledger_path, acceptance)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(stylize("Bounty accepted.", fg="green", bold=True))
    click.echo(f"campaign_id={campaign.id}")
    click.echo(f"solver_hotkey={hotkey}")
    if solver_uid is not None:
        click.echo(f"solver_uid={solver_uid}")
    click.echo(f"accepted_unix={acceptance.accepted_unix}")
    click.echo(f"ledger={settings.campaign_acceptance_ledger_path}")


@main.group("target", invoke_without_command=True, hidden=True)
@click.pass_context
def target_group(ctx: click.Context) -> None:
    """Show the active target and solved ledger."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(target_show_cmd, target_id=None)


@target_group.command("show")
@click.argument("target_id", required=False)
def target_show_cmd(target_id: str | None) -> None:
    from lemma.cli.problem_views import echo_challenge_separator, echo_lean_source, echo_problem_card
    from lemma.ledger import current_solver_set
    from lemma.problems.known_theorems import known_theorems_manifest_sha256

    settings = LemmaSettings()
    src = get_problem_source(settings)
    try:
        current_block, _chain_error = _current_block_or_none(settings)
        seed = cadence_window(int(current_block or 0), settings.cadence_window_blocks).seed
        problem = src.get(target_id.strip()) if target_id else cadence_problem(src, seed)
    except KeyError as exc:
        raise click.ClickException(f"unknown target id: {target_id}") from exc
    solver_set = current_solver_set(settings.solved_ledger_path)
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    click.echo(stylize("Lemma target", fg="cyan", bold=True))
    click.echo(stylize(f"manifest_sha256={manifest_sha}", dim=True))
    if solver_set is None:
        solver_text = "active_solver_uids=<none yet>"
    else:
        uids = ",".join(str(uid) for uid in solver_set.solver_uids)
        solver_text = f"active_solver_uids={uids} last_solved={solver_set.target_id}"
    click.echo(stylize(solver_text, fg="yellow"))
    click.echo("")
    if target_id is None:
        _echo_theorem_window(settings)
        click.echo("")
    echo_problem_card(problem, heading="Active theorem" if target_id is None else "Theorem")
    ref = problem.extra.get("human_proof_reference")
    if isinstance(ref, dict):
        click.echo(stylize("proof_reference=" + str(ref.get("citation") or ""), dim=True))
    review = problem.extra.get("review")
    if isinstance(review, dict):
        click.echo(stylize("duplicate_check=" + str(review.get("duplicate_check") or ""), dim=True))
    echo_challenge_separator()
    echo_lean_source(problem.challenge_source())


@target_group.command("ledger")
def target_ledger_cmd() -> None:
    from lemma.ledger import load_solved_ledger, resolved_solved_ledger_path

    settings = LemmaSettings()
    path = resolved_solved_ledger_path(settings.solved_ledger_path)
    entries = load_solved_ledger(settings.solved_ledger_path)
    click.echo(stylize("Lemma ledger", fg="cyan", bold=True))
    click.echo(stylize(str(path), dim=True))
    if not entries:
        click.echo("No solved targets yet.")
        return
    for entry in entries:
        uids = ",".join(str(uid) for uid in entry.solver_uids)
        proofs = ",".join(solver.proof_sha256[:16] for solver in entry.solvers)
        commitments = ",".join(
            (solver.commitment_hash or "")[:16] for solver in entry.solvers if solver.commitment_hash
        )
        click.echo("")
        click.echo(stylize(entry.target_id, fg="green", bold=True))
        click.echo(stylize("  solver_uid(s) ", dim=True) + stylize(uids, fg="yellow", bold=True))
        click.echo(stylize("  proof(s)      ", dim=True) + proofs)
        if commitments:
            click.echo(stylize("  commitment(s) ", dim=True) + commitments)
        click.echo(stylize("  block         ", dim=True) + str(entry.accepted_block))


def _current_block_or_none(settings: LemmaSettings) -> tuple[int | None, str | None]:
    try:
        from lemma.common.subtensor import get_subtensor

        return int(get_subtensor(settings).get_current_block()), None
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _phase_or_none(settings: LemmaSettings, current_block: int):
    from lemma.ledger import matching_solved_ledger
    from lemma.lifecycle import target_phase

    src = get_problem_source(settings)
    hashes = {p.id: p.theorem_statement_sha256() for p in src.all_problems()}
    ledger = matching_solved_ledger(settings.solved_ledger_path, hashes)
    return target_phase(settings, ledger, current_block)


def _wallet_hotkey_address(settings: LemmaSettings, role: str = "miner") -> str | None:
    try:
        import bittensor as bt

        wallet_cold, wallet_hot = _wallet_names(settings, role)
        return str(bt.Wallet(name=wallet_cold, hotkey=wallet_hot).hotkey.ss58_address)
    except Exception:  # noqa: BLE001
        return None


def _registration_text(settings: LemmaSettings, hotkey: str | None) -> str:
    if hotkey is None:
        return "wallet hotkey unavailable"
    try:
        from lemma.common.subtensor import get_subtensor

        uid = get_subtensor(settings).get_uid_for_hotkey_on_subnet(hotkey, settings.netuid)
    except Exception:  # noqa: BLE001
        return "registration unknown"
    return "not registered" if uid is None else f"registered uid={uid}"


def _miner_uid_or_none(settings: LemmaSettings) -> int | None:
    hotkey = _wallet_hotkey_address(settings, "miner")
    if hotkey is None:
        return None
    try:
        from lemma.common.subtensor import get_subtensor

        uid = get_subtensor(settings).get_uid_for_hotkey_on_subnet(hotkey, settings.netuid)
    except Exception:  # noqa: BLE001
        return None
    return None if uid is None else int(uid)


@main.command("status", help="Show your next Lemma step.")
def status_cmd() -> None:
    from lemma.submissions import pending_submission_for_problem

    settings = LemmaSettings()
    click.echo(stylize("Lemma status", fg="cyan", bold=True))
    phase_name: str | None = None
    proof_hint: str | None = None
    current_block, chain_error = _current_block_or_none(settings)
    try:
        problem = _active_problem_or_click(settings, current_block, _miner_uid_or_none(settings))
        click.echo(_kv("target", problem.id, fg="green"))
    except click.ClickException as exc:
        click.echo(_kv("target", str(exc), fg="yellow"))
        problem = None
    _echo_theorem_window(settings)

    if current_block is None:
        click.echo(_kv("chain", "unavailable", fg="yellow"))
        if chain_error:
            click.echo(stylize("       " + chain_error[:160], dim=True))
    else:
        click.echo(_kv("block", current_block, fg="cyan"))
        try:
            phase = _phase_or_none(settings, current_block)
            phase_name = phase.name
            phase_color = "green" if phase.name == "reveal" else "yellow"
            click.echo(_kv("phase", phase.name, fg=phase_color))
            click.echo(_kv("reveal", f"block {phase.reveal_block}", fg="cyan"))
            if phase.blocks_until_reveal:
                eta_seconds = int(phase.blocks_until_reveal * settings.block_time_sec_estimate)
                click.echo(_kv("eta", format_eta(eta_seconds), fg="magenta"))
        except Exception as exc:  # noqa: BLE001
            phase_error = str(exc)
            click.echo(_kv("phase", phase_error, fg="yellow"))

    if problem is not None:
        pending = pending_submission_for_problem(settings.miner_submissions_path, problem)
        if pending is None:
            proof_text = "no local proof"
            next_step = "lemma mine"
        elif pending.commitment_status == "committed":
            if phase_name == "reveal":
                proof_text = "committed; reveal open"
                proof_hint = "keep lemma mine running; proof is ready for validator polling"
            else:
                proof_text = "committed; waiting reveal"
                proof_hint = "miner can run now; proof stays private until reveal"
            next_step = "lemma mine"
        elif pending.commitment_status == "commit_window_closed" and phase_name == "reveal":
            proof_text = "missed commit window"
            next_step = "lemma mine"
        elif pending.commitment_status == "commit_window_closed":
            proof_text = "verified, needs commit"
            next_step = "lemma mine --retry-commit"
        elif not pending.proof_nonce:
            proof_text = "stale local proof"
            next_step = "lemma mine --replace"
        else:
            proof_text = pending.commitment_status
            next_step = "lemma mine --retry-commit"
        proof_color = "green" if proof_text.startswith("committed") else "yellow"
        click.echo(_kv("proof", proof_text, fg=proof_color))
        if proof_hint:
            click.echo(_kv("serve", proof_hint, fg="cyan"))
            click.echo(_kv("eta", _poll_eta(settings), fg="magenta"))
            click.echo(_kv("dashboard", settings.public_dashboard_url, fg="bright_blue"))
            click.echo(_kv("ledger", "lemma target ledger (local validator/operator ledger)", fg="cyan"))
    else:
        next_step = "lemma target ledger"

    hotkey = _wallet_hotkey_address(settings)
    click.echo(_kv("wallet", f"{settings.wallet_cold}/{settings.wallet_hot}", fg="green"))
    click.echo(_kv("hotkey", hotkey or "unavailable", fg="green" if hotkey else "yellow"))
    registration = _registration_text(settings, hotkey)
    click.echo(_kv("subnet", registration, fg="green" if registration.startswith("registered") else "yellow"))
    click.echo("")
    click.echo(stylize("Next: ", fg="cyan", bold=True) + _cmd(next_step))


@main.command("validate", help="Start validator after setup checks.")
@click.option("--wallet", "wallet_cold", help="Coldkey/wallet name for the validator.")
@click.option("--hotkey", "wallet_hot", help="Hotkey name for the validator.")
def validate_cmd(wallet_cold: str | None, wallet_hot: str | None) -> None:
    from lemma.cli.validator_check import run_validator_check
    from lemma.validator.service import ValidatorService

    settings = _settings_with_wallet_options(LemmaSettings(), role="validator", wallet=wallet_cold, hotkey=wallet_hot)
    code = run_validator_check(settings)
    if code != 0:
        click.echo(
            stylize("Run ", fg="yellow")
            + _cmd("lemma setup --role validator")
            + stylize(" to fix the setup values above.", fg="yellow"),
        )
        raise SystemExit(code)
    click.echo(stylize("Starting validator.", fg="green", bold=True))
    ValidatorService(settings, dry_run=False).run_blocking()


@main.command("submit", hidden=True)
@click.option("--problem", "problem_id")
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--verify/--no-verify", "do_verify", default=True, help="Verify before storing the proof.")
@click.option("--paste", is_flag=True, help="Paste a full Submission.lean file, then press Ctrl-D.")
@click.option("--host-lean", is_flag=True, help="With --verify, use host lake. Requires LEMMA_ALLOW_HOST_LEAN=1.")
def submit_cmd(
    problem_id: str | None,
    submission_path: Path | None,
    do_verify: bool,
    paste: bool,
    host_lean: bool,
) -> None:
    from lemma.cli.problem_views import echo_challenge_separator, echo_lean_source, echo_problem_card
    from lemma.problems.factory import get_problem_source

    settings = LemmaSettings()
    if paste and submission_path is not None:
        raise click.ClickException("Use either --paste or --submission, not both.")
    if problem_id is None:
        src = get_problem_source(settings)
        try:
            problem = src.sample(seed=0)
        except ValueError as exc:
            raise click.ClickException("All known theorem targets are solved.") from exc
    else:
        problem = _resolve_problem_or_click(settings, problem_id)

    if submission_path is not None:
        _submit_proof(
            settings,
            problem_id=problem.id,
            proof_script=submission_path.read_text(encoding="utf-8"),
            do_verify=do_verify,
            host_lean=host_lean,
        )
        return

    click.echo(stylize("Lemma submit", fg="cyan", bold=True))
    click.echo("This stores a Lean proof so your miner can serve it to validators.\n")
    echo_problem_card(problem, heading="Current theorem" if problem_id is None else "Theorem")
    echo_challenge_separator()
    echo_lean_source(problem.challenge_source())
    click.echo("")
    if not click.confirm("Ready to enter a proof for this target?", default=False):
        click.echo(stylize("No proof stored.", fg="yellow"))
        return

    if paste:
        click.echo(stylize("Paste your full Submission.lean file below.", fg="cyan"))
        click.echo(stylize("After the final line, press Enter once, then Ctrl-D on the empty line.", fg="cyan"))
        proof_script = click.get_text_stream("stdin").read()
    else:
        click.echo(stylize("Opening Submission.lean in your editor. Replace sorry, save, and close.", fg="cyan"))
        edited = click.edit(text=problem.submission_stub(), extension=".lean")
        if edited is None or edited == problem.submission_stub():
            click.echo(stylize("No proof stored. The submission was empty or unchanged.", fg="yellow"))
            return
        proof_script = edited

    if not proof_script.strip():
        click.echo(stylize("No proof stored. The submission was empty.", fg="yellow"))
        return
    _submit_proof(settings, problem_id=problem.id, proof_script=proof_script, do_verify=do_verify, host_lean=host_lean)


def _submit_proof(
    settings: LemmaSettings,
    *,
    problem_id: str,
    proof_script: str,
    do_verify: bool,
    host_lean: bool,
    concise: bool = False,
    show_next: bool = True,
    publish_commit: bool = False,
):
    from lemma.commitments import new_nonce
    from lemma.lean.verify_runner import run_lean_verify
    from lemma.submissions import resolved_submissions_path, save_pending_submission

    problem = _resolve_problem_or_click(settings, problem_id)
    verify_reason = "not_run"
    build_seconds = 0.0
    if do_verify:
        if host_lean and not settings.allow_host_lean:
            raise click.ClickException("Host Lean is disabled. Set LEMMA_ALLOW_HOST_LEAN=1 or omit --host-lean.")
        click.echo(stylize("Checking proof with Lean...", fg="cyan"))
        eff = settings.model_copy(update={"lean_use_docker": not host_lean and settings.lean_use_docker})
        try:
            vr = run_lean_verify(
                eff,
                verify_timeout_s=settings.lean_verify_timeout_s,
                problem=problem,
                proof_script=proof_script,
            )
        except Exception as exc:
            raise click.ClickException(f"Lean could not run local verification: {exc}") from exc
        if not vr.passed:
            raise click.ClickException(f"Lean rejected this proof: {vr.reason}\n{vr.stderr_tail}")
        verify_reason = vr.reason
        build_seconds = float(vr.build_seconds)
    entry = save_pending_submission(
        settings.miner_submissions_path,
        problem,
        proof_script,
        proof_nonce=new_nonce(),
    )
    heading = (
        "Lean accepted this proof. Stored for your miner."
        if do_verify
        else "Proof stored without local Lean check."
    )
    click.echo(stylize(heading, fg="green" if do_verify else "yellow", bold=True))
    click.echo(f"target_id={entry.target_id}")
    click.echo(f"verified={str(do_verify).lower()}")
    click.echo(f"verify_reason={verify_reason}")
    click.echo(f"build_seconds={build_seconds:.2f}")
    click.echo(f"proof_sha256={entry.proof_sha256}")
    click.echo(f"store={resolved_submissions_path(settings.miner_submissions_path)}")
    active_settings = settings
    if do_verify and publish_commit:
        try:
            entry = _publish_pending_commitment(settings, problem, entry)
        except CommitWindowClosedError as exc:
            raise click.ClickException(str(exc)) from exc
    if concise:
        if entry.commitment_status == "committed":
            click.echo(stylize("Your private commitment is on-chain.", fg="green", bold=True))
            click.echo(f"commitment_block={entry.committed_block or ''}")
            click.echo(f"reveal_block={entry.reveal_block or ''}")
        else:
            click.echo(stylize("Proof stored, but it is not committed yet.", fg="yellow", bold=True))
            click.echo("Run `lemma mine --retry-commit`.")
        return entry, active_settings
    click.echo(f"commit_status={entry.commitment_status}")
    click.echo(f"commitment_hash={entry.commitment_hash or ''}")
    click.echo(f"commitment_block={entry.committed_block or ''}")
    click.echo(f"commit_cutoff_block={entry.commit_cutoff_block or ''}")
    click.echo(f"reveal_block={entry.reveal_block or ''}")
    click.echo(f"ready_to_reveal={str(entry.commitment_status == 'committed').lower()}")
    if show_next:
        click.echo("")
        click.echo(stylize("Next:", fg="cyan", bold=True))
        if entry.commitment_status == "committed":
            click.echo("Run " + _cmd("lemma miner start") + " so validators can poll this proof after reveal opens.")
        else:
            click.echo("Run " + _cmd("lemma commit --problem " + problem.id) + " before starting the miner.")
        click.echo(
            f"Keep it running until your UID appears on {settings.public_dashboard_url} "
            "or in `lemma target ledger` if you have the validator/operator ledger locally.",
        )
        click.echo(
            f"Wait hint: validators poll on their own schedule; this config uses "
            f"about {int(active_settings.validator_poll_interval_s)}s between polls, plus Lean verify time.",
        )
        click.echo("Validators do not answer this command directly.")
        click.echo(
            f"Accepted solvers appear on {settings.public_dashboard_url} "
            "and in `lemma target ledger` if you have the validator/operator ledger locally.",
        )
    return entry, active_settings


def _publish_pending_commitment(settings: LemmaSettings, problem, entry):
    import bittensor as bt

    from lemma.commitments import build_proof_commitment
    from lemma.common.subtensor import get_subtensor
    from lemma.lifecycle import target_phase
    from lemma.problems.known_theorems import known_theorems_manifest_sha256
    from lemma.submissions import update_pending_submission

    subtensor = get_subtensor(settings)
    current_block = int(subtensor.get_current_block())
    try:
        phase = target_phase(settings, [], current_block)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if phase.name != "commit":
        status = "commit_window_closed" if phase.name == "reveal" else "commit_window_pending"
        updated = replace(
            entry,
            commitment_status=status,
            target_start_block=phase.target_start_block,
            commit_cutoff_block=phase.commit_cutoff_block,
            reveal_block=phase.reveal_block,
        )
        update_pending_submission(settings.miner_submissions_path, updated)
        if phase.name == "reveal":
            raise CommitWindowClosedError(
                "Commit window is closed for this target. The proof is verified and stored, "
                "but it cannot be committed to this window.\n"
                "Next: wait for the next 100-block cadence window, then run `lemma mine` again.",
                current_block=current_block,
                entry=updated,
            )
        raise click.ClickException(
            f"Commit window has not opened yet. Retry at block {phase.target_start_block}.",
        )

    wallet = bt.Wallet(name=settings.wallet_cold, hotkey=settings.wallet_hot)
    miner_hotkey = wallet.hotkey.ss58_address
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    if not entry.proof_nonce:
        raise click.ClickException("pending proof is missing its secret nonce; resubmit the proof")
    commitment = build_proof_commitment(
        netuid=settings.netuid,
        miner_hotkey=miner_hotkey,
        manifest_sha256=manifest_sha,
        problem=problem,
        proof_hash=entry.proof_sha256,
        nonce=entry.proof_nonce,
    )
    out = subtensor.set_commitment(wallet=wallet, netuid=settings.netuid, data=commitment.payload_text)
    ok, message = _chain_outcome(out)
    committed_block = int(subtensor.get_current_block()) if ok else None
    updated = replace(
        entry,
        commitment_hash=commitment.commitment_hash,
        commitment_payload=commitment.payload_text,
        commitment_status="committed" if ok else "commit_failed",
        committed_hotkey=miner_hotkey,
        committed_block=committed_block,
        manifest_sha256=manifest_sha,
        target_start_block=phase.target_start_block,
        commit_cutoff_block=phase.commit_cutoff_block,
        reveal_block=phase.reveal_block,
    )
    update_pending_submission(settings.miner_submissions_path, updated)
    if not ok:
        raise click.ClickException(
            "Proof stored, but chain commitment failed. "
            f"Run `lemma mine --retry-commit` to retry. Advanced: "
            f"`lemma commit --problem {problem.id}`. {message}",
        )
    return updated


@main.command("commit", help="Publish a stored proof commitment.", hidden=True)
@click.option("--problem", "problem_id", required=True)
def commit_cmd(problem_id: str) -> None:
    from lemma.submissions import pending_submission_for_problem, resolved_submissions_path

    settings = LemmaSettings()
    problem = _resolve_problem_or_click(settings, problem_id)
    entry = pending_submission_for_problem(settings.miner_submissions_path, problem)
    if entry is None:
        raise click.ClickException(f"no stored proof for target: {problem_id}")
    entry = _publish_pending_commitment(settings, problem, entry)
    click.echo(stylize("Proof commitment published.", fg="green", bold=True))
    click.echo(f"target_id={entry.target_id}")
    click.echo(f"commitment_hash={entry.commitment_hash}")
    click.echo(f"commitment_block={entry.committed_block}")
    click.echo(f"commit_cutoff_block={entry.commit_cutoff_block}")
    click.echo(f"reveal_block={entry.reveal_block}")
    click.echo(f"store={resolved_submissions_path(settings.miner_submissions_path)}")


@main.group("miner", invoke_without_command=True, help="Serve manually submitted proofs to validators.", hidden=True)
@click.pass_context
def miner_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@miner_group.command("start")
def miner_start_cmd() -> None:
    from lemma.miner.service import MinerService

    settings = LemmaSettings()
    setup_logging(settings.log_level)
    MinerService(settings).run()


@main.group("dashboard", invoke_without_command=True, help="Export public static dashboard data.", hidden=True)
@click.pass_context
def dashboard_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@dashboard_group.command("export")
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
)
def dashboard_export_cmd(output_path: Path) -> None:
    from lemma.dashboard import build_miner_dashboard, write_miner_dashboard

    settings = LemmaSettings()
    write_miner_dashboard(output_path, build_miner_dashboard(settings))
    click.echo(f"wrote={output_path}")


@dashboard_group.command("export-bounties")
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
)
def dashboard_export_bounties_cmd(output_path: Path) -> None:
    from lemma.dashboard import build_bounty_dashboard, write_miner_dashboard

    settings = LemmaSettings()
    write_miner_dashboard(output_path, build_bounty_dashboard(settings))
    click.echo(f"wrote={output_path}")


@dashboard_group.command("publish")
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(file_okay=False, path_type=Path),
    required=True,
)
def dashboard_publish_cmd(output_dir: Path) -> None:
    from lemma.dashboard import publish_public_dashboards

    settings = LemmaSettings()
    cadence_path, bounties_path = publish_public_dashboards(output_dir, settings)
    click.echo(f"wrote={cadence_path}")
    click.echo(f"wrote={bounties_path}")


@main.group(
    "validator",
    invoke_without_command=True,
    help="Poll miners, Lean verify, and set miner weights.",
    hidden=True,
)
@click.pass_context
def validator_group(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help(), color=colors_enabled())


@validator_group.command("start")
def validator_start_cmd() -> None:
    from lemma.validator.service import ValidatorService

    ValidatorService(LemmaSettings(), dry_run=False).run_blocking()


@validator_group.command("dry-run")
def validator_dry_run_cmd() -> None:
    from lemma.validator.service import ValidatorService

    ValidatorService(LemmaSettings(), dry_run=True).run_blocking()


@validator_group.command("check")
def validator_check_cmd() -> None:
    from lemma.cli.validator_check import run_validator_check

    raise SystemExit(run_validator_check(LemmaSettings()))


@main.command("verify", hidden=True)
@click.option("--problem", "problem_id", required=True)
@click.option(
    "--submission",
    "submission_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option("--host-lean", is_flag=True, help="Run lake on host. Requires LEMMA_ALLOW_HOST_LEAN=1.")
def verify_cmd(problem_id: str, submission_path: Path, host_lean: bool) -> None:
    from lemma.lean.verify_runner import run_lean_verify

    settings = LemmaSettings()
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException("Host Lean is disabled. Set LEMMA_ALLOW_HOST_LEAN=1 or omit --host-lean.")
    proof_script = submission_path.read_text(encoding="utf-8")
    problem = _resolve_problem_or_click(settings, problem_id)
    eff = settings.model_copy(update={"lean_use_docker": not host_lean and settings.lean_use_docker})
    vr = run_lean_verify(
        eff,
        verify_timeout_s=settings.lean_verify_timeout_s,
        problem=problem,
        proof_script=proof_script,
    )
    click.echo(vr.model_dump_json(indent=2))
    sys.exit(0 if vr.passed else 1)


@main.command("meta", hidden=True)
@click.option("--raw", is_flag=True)
def meta_cmd(raw: bool) -> None:
    import json

    from lemma.problems.known_theorems import known_theorems_manifest, known_theorems_manifest_sha256
    from lemma.validator.profile import validator_profile_dict, validator_profile_sha256

    settings = LemmaSettings()
    manifest_sha = known_theorems_manifest_sha256(settings.known_theorems_manifest_path)
    profile = validator_profile_dict(settings)
    profile_sha = validator_profile_sha256(settings)
    if raw:
        click.echo(f"lemma_version={__version__}")
        click.echo(f"problem_source={settings.problem_source}")
        click.echo(f"known_theorems_manifest_sha256={manifest_sha}")
        click.echo(
            "known_theorems_manifest_json="
            + json.dumps(known_theorems_manifest(settings.known_theorems_manifest_path), sort_keys=True),
        )
        click.echo(f"validator_profile_sha256={profile_sha}")
        click.echo("validator_profile_json=" + json.dumps(profile, sort_keys=True))
        return
    click.echo(stylize("Lemma fingerprints", fg="cyan", bold=True))
    click.echo(f"known_theorems_manifest_sha256={manifest_sha}")
    click.echo(f"validator_profile_sha256={profile_sha}")
