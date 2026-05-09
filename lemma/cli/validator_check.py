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
from lemma.common.config import LemmaSettings, validator_judge_stack_strict_issue
from lemma.common.subtensor import get_subtensor
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.generated import generated_registry_sha256
from lemma.validator.judge_profile_attest import judge_profile_peer_check_errors


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
        click.echo(
            stylize(
                "Skipping validator start. Your shell prompt should appear below — "
                "if not, press Enter once.",
                dim=True,
            ),
        )
        finish_cli_output()
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
    click.echo(
        stylize("(run before `lemma validator start` — not the same as `lemma validator-dry`)\n", dim=True),
        nl=False,
    )

    # --- Subnet pin requirements (same gates as ValidatorService) ---
    if not (settings.judge_profile_expected_sha256 or "").strip():
        fatal.append(
            "lemma validator requires JUDGE_PROFILE_SHA256_EXPECTED in `.env` "
            "(run `lemma-cli configure subnet-pins` or copy from `lemma meta --raw`).",
        )
    if (settings.problem_source or "").strip().lower() == "generated":
        if not (settings.generated_registry_expected_sha256 or "").strip():
            fatal.append(
                "lemma validator requires LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED when "
                "LEMMA_PROBLEM_SOURCE=generated (run `lemma-cli configure subnet-pins`).",
            )
    if (settings.problem_source or "").strip().lower() == "frozen":
        if not settings.lemma_dev_allow_frozen_problem_source:
            fatal.append(
                "LEMMA_PROBLEM_SOURCE=frozen requires LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1 "
                "(public eval catalog). Use generated for subnet traffic — see docs/catalog-sources.md",
            )

    judge_policy = validator_judge_stack_strict_issue(settings)
    if judge_policy:
        fatal.append(judge_policy)

    # --- Judge keys ---
    jp = (settings.judge_provider or "chutes").lower()
    if jp in ("openai", "chutes"):
        if not (settings.judge_openai_api_key_resolved() or "").strip():
            fatal.append(
                "JUDGE_OPENAI_API_KEY (or legacy OPENAI_API_KEY) missing — live validator cannot score miners.",
            )
    elif jp == "anthropic":
        if not (settings.anthropic_api_key or "").strip():
            fatal.append(
                "ANTHROPIC_API_KEY missing — live validator cannot score miners.",
            )

    click.echo(
        stylize(
            f"INFO scoring  LEMMA_SCORE_PROOF_WEIGHT={settings.lemma_score_proof_weight}  "
            f"LEMMA_REPUTATION_EMA_ALPHA={settings.lemma_reputation_ema_alpha}  "
            f"LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA={settings.lemma_reputation_verify_credibility_alpha}  "
            f"LEMMA_REPUTATION_CREDIBILITY_EXPONENT={settings.lemma_reputation_credibility_exponent}  "
            f"LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS={int(settings.lemma_proof_intrinsic_strip_comments)}  "
            f"LEMMA_EPOCH_PROBLEM_COUNT={settings.lemma_epoch_problem_count}  "
            f"LEMMA_MINER_VERIFY_ATTEST_ENABLED={int(settings.lemma_miner_verify_attest_enabled)}  "
            "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION="
            f"{settings.lemma_miner_verify_attest_spot_verify_fraction}  "
            "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT_SET="
            f"{int(bool((settings.lemma_miner_verify_attest_spot_verify_salt or '').strip()))}  "
            f"LEMMA_COMMIT_REVEAL_ENABLED={int(settings.lemma_commit_reveal_enabled)}  "
            f"LEMMA_JUDGE_PROFILE_ATTEST_ENABLED={int(settings.lemma_judge_profile_attest_enabled)}  "
            "(docs/incentive_migration.md)",
            dim=True,
        ),
    )

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
                f"{actual_j[:16]}… — align judge env or refresh `lemma-cli configure subnet-pins`.",
            )
        else:
            click.echo(stylize("OK judge pin   matches live judge_profile_sha256", fg="green"))
    else:
        click.echo(
            stylize(
                "FAIL judge pin  JUDGE_PROFILE_SHA256_EXPECTED required for validators",
                fg="red",
                bold=True,
            ),
            err=True,
        )

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
            click.echo(
                stylize(
                    "FAIL registry pin  LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED required when "
                    "LEMMA_PROBLEM_SOURCE=generated",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )

    # --- Judge profile peer attest (optional) ---
    if settings.lemma_judge_profile_attest_enabled:
        if settings.lemma_judge_profile_attest_allow_skip:
            click.echo(
                stylize(
                    "WARN judge attest  LEMMA_JUDGE_PROFILE_ATTEST_SKIP=1 — peer URLs not checked",
                    fg="yellow",
                ),
            )
        attest_errs = judge_profile_peer_check_errors(settings)
        fatal.extend(attest_errs)
        if attest_errs:
            click.echo(
                stylize(
                    "FAIL judge attest  peer URLs did not match local judge_profile_sha256 — see above",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )
        elif not settings.lemma_judge_profile_attest_allow_skip:
            click.echo(
                stylize(
                    "OK judge attest  peer URLs agree with local judge_profile_sha256",
                    fg="green",
                ),
            )

    # --- Lean image / verify path ---
    img = (settings.lean_sandbox_image or "").strip()
    use_docker = settings.lean_use_docker
    remote_u = (settings.lean_verify_remote_url or "").strip()

    if remote_u:
        click.echo(
            stylize(
                f"OK Lean remote  verify delegated to worker ({remote_u!r}) — run `lemma lean-worker` there "
                "with matching `.env` (Docker/cache on worker host)",
                fg="green",
            ),
        )
    elif use_docker:
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
        click.echo(
            stylize(
                "FAIL Lean      LEMMA_USE_DOCKER=false — `lemma validator` cannot start "
                "(validators must use Docker). Set LEMMA_USE_DOCKER=true.",
                fg="red",
                bold=True,
            ),
            err=True,
        )
        fatal.append("LEMMA_USE_DOCKER=false — lemma validator requires Docker (LEMMA_USE_DOCKER=true).")

    if use_docker and not remote_u:
        cache_dir = settings.lean_verify_workspace_cache_dir
        worker = (settings.lemma_lean_docker_worker or "").strip()
        if cache_dir is not None:
            click.echo(
                stylize(f"INFO Lean cache workspace dir set ({cache_dir}) — warm `.lake` per template", dim=True),
            )
        else:
            click.echo(
                stylize(
                    "INFO Lean speed  set LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR + optional "
                    "LEMMA_LEAN_DOCKER_WORKER for exec-based verify (see docs/validator.md)",
                    dim=True,
                ),
            )
        if worker:
            click.echo(
                stylize(
                    f"OK Lean worker  LEMMA_LEAN_DOCKER_WORKER={worker!r} — verify uses `docker exec`",
                    fg="green",
                ),
            )
        else:
            click.echo(
                stylize(
                    "INFO Lean speed  LEMMA_LEAN_DOCKER_WORKER unset — each verify starts a new container "
                    "(`scripts/start_lean_docker_worker.sh` + add LEMMA_LEAN_DOCKER_WORKER to `.env`)",
                    dim=True,
                ),
            )

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
