"""Pre-flight checks before ``lemma validator`` (RPC, registration, judge, Lean image, pins)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from typing import Literal

import bittensor as bt
import click

from lemma.cli.style import finish_cli_output, flush_stdio, stylize
from lemma.common.config import LemmaSettings, canonical_openai_judge_model_issue
from lemma.common.subtensor import get_subtensor
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.generated import generated_registry_sha256


def _print_ready_footer(*, outcome: Literal["ok", "warn"]) -> None:
    """READY banner + next-step line + status line + trailing newline."""
    click.echo("")
    click.echo(stylize("READY", fg="green", bold=True))
    click.echo(
        stylize(
            "  Next: lemma validator start    (append --dry-run to skip set_weights)",
            dim=True,
        )
    )
    if outcome == "warn":
        click.echo(
            stylize("validator-check: WARN — see above (risky for mainnet scoring)", fg="yellow"),
            err=True,
        )
    else:
        click.echo(stylize("validator-check: OK", fg="green"))
    click.echo("")


def _interactive_validator_start_prompt_ok() -> bool:
    """TTY-only so scripts and CI never block waiting for input."""
    if os.environ.get("LEMMA_VALIDATOR_CHECK_NO_PROMPT", "").strip().lower() in ("1", "true", "yes"):
        return False
    return sys.stdin.isatty()


def _maybe_prompt_validator_start(settings: LemmaSettings, *, had_warnings: bool) -> None:
    """Interactive handoff to `lemma validator start` (same process)."""
    if had_warnings:
        ok = click.confirm(
            "Start the scoring loop now (`lemma validator start`)? "
            "Warnings above may affect scoring.",
            default=False,
        )
    else:
        ok = click.confirm(
            "Start the scoring loop now (`lemma validator start`)?",
            default=False,
        )
    if not ok:
        flush_stdio()
        return
    from lemma.validator.service import ValidatorService

    ValidatorService(settings, dry_run=False).run_blocking()
    click.echo("")
    flush_stdio()


def _docker_image_available(image: str) -> bool:
    if not shutil.which("docker"):
        return False
    try:
        r = subprocess.run(
            ["docker", "image", "inspect", image],
            capture_output=True,
            timeout=30,
            check=False,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def run_validator_check(settings: LemmaSettings) -> int:
    """Print checklist; return 0 if OK to start, 1 if blocking issues."""
    fatal: list[str] = []
    warn: list[str] = []

    click.echo(stylize("Validator pre-flight", fg="cyan", bold=True))
    click.echo(stylize("(run before `lemma validator` — not the same as `lemma validator-dry`)\n", dim=True), nl=False)

    # --- Enforce-pins policy (same gates as ValidatorService) ---
    if settings.validator_enforce_published_meta:
        if not (settings.judge_profile_expected_sha256 or "").strip():
            fatal.append(
                "LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META=1 but JUDGE_PROFILE_SHA256_EXPECTED is empty "
                "(run `lemma configure subnet-pins` after aligning judge env).",
            )
        elif (
            (settings.problem_source or "").strip().lower() == "generated"
            and not (settings.generated_registry_expected_sha256 or "").strip()
        ):
            fatal.append(
                "LEMMA_VALIDATOR_ENFORCE_PUBLISHED_META=1 + generated source but "
                "LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED is empty.",
            )

    # --- Judge keys ---
    jp = (settings.judge_provider or "openai").lower()
    if jp == "openai":
        if not (settings.openai_api_key or "").strip():
            warn.append(
                "OPENAI_API_KEY missing — validator will use FakeJudge (not for production scoring).",
            )
    elif jp == "anthropic":
        if not (settings.anthropic_api_key or "").strip():
            warn.append(
                "ANTHROPIC_API_KEY missing — validator will use FakeJudge (not for production scoring).",
            )

    canon_issue = canonical_openai_judge_model_issue(settings)
    if canon_issue:
        fatal.append(canon_issue)

    # --- Chain + wallet / UID ---
    subtensor: bt.Subtensor | None = None
    head: int | None = None
    netuid = settings.netuid
    try:
        subtensor = get_subtensor(settings)
        head = int(subtensor.get_current_block())
        click.echo(stylize(f"OK chain RPC  head_block={head}", fg="green"))
    except Exception as e:  # noqa: BLE001
        fatal.append(f"chain RPC failed: {e}")

    v_cold, v_hot = settings.validator_wallet_names()
    try:
        wallet = bt.Wallet(name=v_cold, hotkey=v_hot)
        hk = wallet.hotkey.ss58_address
        click.echo(stylize(f"OK wallet    cold={v_cold!r} hot={v_hot!r}", fg="green"))
        if v_cold != settings.wallet_cold or v_hot != settings.wallet_hot:
            click.echo(
                stylize(
                    "             (validator keys — miner axon still uses BT_WALLET_COLD/HOT)",
                    dim=True,
                ),
            )
        if subtensor is not None:
            uid = subtensor.get_uid_for_hotkey_on_subnet(hk, netuid)
            if uid is None:
                warn.append(
                    f"Hotkey has no UID on subnet netuid={netuid} — register on subnet before validator rewards "
                    f"(VALIDATOR_ABORT_IF_NOT_REGISTERED may skip rounds).",
                )
                click.echo(stylize(f"WARN subnet UID  none on netuid={netuid}", fg="yellow"), err=True)
            else:
                click.echo(stylize(f"OK subnet UID  {uid} on netuid={netuid}", fg="green"))
    except Exception as e:  # noqa: BLE001
        warn.append(f"wallet / UID check failed: {e}")
        click.echo(stylize(f"WARN wallet    {e}", fg="yellow"), err=True)

    # --- Pin drift ---
    exp_j = (settings.judge_profile_expected_sha256 or "").strip().lower()
    if exp_j:
        actual_j = judge_profile_sha256(settings).strip().lower()
        if actual_j != exp_j:
            fatal.append(
                f"JUDGE_PROFILE_SHA256_EXPECTED mismatch: env expects {exp_j[:16]}… but live `lemma meta` is "
                f"{actual_j[:16]}… — align judge env or refresh `lemma configure subnet-pins`.",
            )
        else:
            click.echo(stylize("OK judge pin   matches live judge_profile_sha256", fg="green"))
    else:
        click.echo(stylize("INFO judge pin  JUDGE_PROFILE_SHA256_EXPECTED unset (optional)", dim=True))

    if (settings.problem_source or "").strip().lower() == "generated":
        exp_g = (settings.generated_registry_expected_sha256 or "").strip().lower()
        if exp_g:
            actual_g = generated_registry_sha256().strip().lower()
            if actual_g != exp_g:
                fatal.append(
                    "LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED mismatch vs current code — align git/release "
                    "or refresh pins.",
                )
            else:
                click.echo(stylize("OK registry pin matches generated_registry_sha256", fg="green"))
        else:
            click.echo(stylize("INFO registry pin LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED unset (optional)", dim=True))

    # --- Lean image ---
    img = (settings.lean_sandbox_image or "").strip()
    use_docker = os.environ.get("LEMMA_USE_DOCKER", "1") != "0"
    if use_docker:
        if _docker_image_available(img):
            click.echo(stylize(f"OK Docker image `{img}` present locally", fg="green"))
        else:
            warn.append(
                f"Docker image `{img}` not found locally — pull/build before epochs "
                f"(see scripts/prebuild_lean_image.sh).",
            )
            click.echo(
                stylize(
                    f"WARN Docker    image `{img}` not found — run prebuild or docker pull",
                    fg="yellow",
                ),
                err=True,
            )
    else:
        click.echo(stylize("INFO Lean       LEMMA_USE_DOCKER=0 — host/path verify only", dim=True))

    # --- Timeout sanity (validator queries miners) ---
    # Compare only to LEMMA_FORWARD_WAIT_MAX_S (clamp ceiling). Per-head forward wait is shorter near rotations
    # and would false-positive almost always if compared to LEMMA_LLM_HTTP_TIMEOUT_S.
    if settings.llm_http_timeout_s > settings.forward_wait_max_s + 0.01:
        warn.append(
            f"LEMMA_LLM_HTTP_TIMEOUT_S ({settings.llm_http_timeout_s:.0f}s) exceeds "
            f"LEMMA_FORWARD_WAIT_MAX_S ({settings.forward_wait_max_s:.0f}s) — "
            "prover cannot fit inside any validator axon wait.",
        )

    click.echo("")
    if fatal:
        click.echo(stylize("BLOCKING", fg="red", bold=True))
        for m in fatal:
            click.echo(stylize(f"  • {m}", fg="red"), err=True)
    if warn:
        click.echo(stylize("WARNINGS", fg="yellow", bold=True))
        for m in warn:
            click.echo(stylize(f"  • {m}", fg="yellow"), err=True)

    click.echo("")
    if fatal:
        click.echo(
            stylize(
                "NOT READY — fix blocking items, then run `lemma validator-check` again.",
                fg="red",
                bold=True,
            ),
            err=True,
        )
        finish_cli_output()
        return 1

    if warn:
        _print_ready_footer(outcome="warn")
        if _interactive_validator_start_prompt_ok():
            _maybe_prompt_validator_start(settings, had_warnings=True)
        finish_cli_output()
        return 0

    _print_ready_footer(outcome="ok")
    if _interactive_validator_start_prompt_ok():
        _maybe_prompt_validator_start(settings, had_warnings=False)
    finish_cli_output()
    return 0
