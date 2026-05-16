"""Pre-flight checks before ``lemma validator`` (RPC, registration, Lean image, pins)."""

from __future__ import annotations

import shutil
import subprocess
from typing import Literal

import bittensor as bt
import click
from loguru import logger

from lemma.cli.style import finish_cli_output, stylize
from lemma.common.config import LemmaSettings
from lemma.common.subtensor import get_subtensor
from lemma.judge.profile import judge_profile_sha256
from lemma.problems.generated import generated_registry_sha256
from lemma.problems.hybrid import problem_supply_registry_sha256
from lemma.validator.service import validator_startup_issues


def _print_ready_footer(*, outcome: Literal["ok", "warn"]) -> None:
    """READY banner + next-step line + status line + trailing newline."""
    click.echo("")
    click.echo(stylize("READY", fg="green", bold=True))
    click.echo(
        stylize(
            "  Next: lemma validator start    (or `lemma validator dry-run` to skip set_weights)",
            dim=True,
        )
    )
    if outcome == "warn":
        click.echo(
            stylize("validator check: WARN — see above (risky for mainnet scoring)", fg="yellow"),
            err=True,
        )
    else:
        click.echo(stylize("validator check: OK", fg="green"))
    click.echo("")


def _docker_image_available(image: str) -> bool:
    try:
        import docker

        client = docker.from_env()
        client.images.get(image)
        return True
    except Exception as e:
        logger.debug("docker SDK image check failed for {}: {}", image, e)

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
    click.echo(stylize("Validator pre-flight", fg="cyan", bold=True))
    click.echo(
        stylize("(run before `lemma validator start` — not the same as `lemma validator config`)\n", dim=True),
        nl=False,
    )
    fatal, warn = validator_startup_issues(settings, dry_run=False)
    startup_fatal = tuple(fatal)

    click.echo(
        stylize(
            "INFO scoring  proof_verification=1  "
            f"LEMMA_SCORING_ROLLING_ALPHA={settings.lemma_scoring_rolling_alpha}  "
            "LEMMA_SCORING_DIFFICULTY_WEIGHTS="
            f"{settings.lemma_scoring_difficulty_easy}/"
            f"{settings.lemma_scoring_difficulty_medium}/"
            f"{settings.lemma_scoring_difficulty_hard}/"
            f"{settings.lemma_scoring_difficulty_extreme}  "
            f"LEMMA_UID_VARIANT_PROBLEMS={int(settings.lemma_uid_variant_problems)}  "
            f"LEMMA_EPOCH_PROBLEM_COUNT={settings.lemma_epoch_problem_count}  "
            f"LEMMA_MINER_VERIFY_ATTEST_ENABLED={int(settings.lemma_miner_verify_attest_enabled)}  "
            "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION="
            f"{settings.lemma_miner_verify_attest_spot_verify_fraction}  "
            "LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT_SET="
            f"{int(bool((settings.lemma_miner_verify_attest_spot_verify_salt or '').strip()))}  "
            f"LEMMA_COMMIT_REVEAL_ENABLED={int(settings.lemma_commit_reveal_enabled)}  "
            f"LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED={int(settings.lemma_judge_profile_attest_enabled)}  "
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
            click.echo(
                stylize(
                    "FAIL profile pin  LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED mismatch vs live `lemma meta`",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )
        else:
            click.echo(stylize("OK profile pin matches live validator profile hash", fg="green"))
    else:
        click.echo(
            stylize(
                "FAIL profile pin  LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED required for validators",
                fg="red",
                bold=True,
            ),
            err=True,
        )

    if (settings.problem_source or "").strip().lower() == "hybrid":
        exp_h = (settings.problem_supply_registry_expected_sha256 or "").strip().lower()
        if exp_h:
            actual_h = problem_supply_registry_sha256(
                generated_weight=settings.lemma_hybrid_generated_weight,
                catalog_weight=settings.lemma_hybrid_catalog_weight,
            ).strip().lower()
            if actual_h != exp_h:
                click.echo(
                    stylize(
                        "FAIL supply pin  LEMMA_PROBLEM_SUPPLY_REGISTRY_SHA256_EXPECTED mismatch vs current code",
                        fg="red",
                        bold=True,
                    ),
                    err=True,
                )
            else:
                click.echo(stylize("OK supply pin matches problem_supply_registry_sha256", fg="green"))
        else:
            click.echo(
                stylize(
                    "FAIL supply pin  LEMMA_PROBLEM_SUPPLY_REGISTRY_SHA256_EXPECTED required when "
                    "LEMMA_PROBLEM_SOURCE=hybrid",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )
    elif (settings.problem_source or "").strip().lower() == "generated":
        exp_g = (settings.generated_registry_expected_sha256 or "").strip().lower()
        if exp_g:
            actual_g = generated_registry_sha256().strip().lower()
            if actual_g != exp_g:
                click.echo(
                    stylize(
                        "FAIL registry pin  LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED mismatch vs current code",
                        fg="red",
                        bold=True,
                    ),
                    err=True,
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

    # --- Validator profile peer attest ---
    if settings.lemma_judge_profile_attest_enabled:
        if settings.lemma_judge_profile_attest_allow_skip:
            click.echo(
                stylize(
                    "WARN profile attest  LEMMA_VALIDATOR_PROFILE_ATTEST_SKIP=1 — peer URLs not checked "
                    "(solo/dev only; not production alignment)",
                    fg="yellow",
                ),
            )
        attest_errs = [
            msg
            for msg in startup_fatal
            if msg.startswith("validator profile attest:") or msg.startswith("LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED")
        ]
        if attest_errs:
            click.echo(
                stylize(
                    "FAIL profile attest  peer URLs did not match local validator profile hash — see above",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )
        elif not settings.lemma_judge_profile_attest_allow_skip:
            click.echo(
                stylize(
                    "OK profile attest  peer URLs agree with local validator profile hash",
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
            if shutil.which("docker"):
                click.echo(
                    stylize(
                        f"OK Lean worker  LEMMA_LEAN_DOCKER_WORKER={worker!r} — verify uses `docker exec`",
                        fg="green",
                    ),
                )
            else:
                warn.append("LEMMA_LEAN_DOCKER_WORKER is set, but Docker CLI is not on PATH; one-shot verify will run.")
                click.echo(
                    stylize(
                        "WARN Lean worker configured, but Docker CLI is missing — one-shot verify will run",
                        fg="yellow",
                    ),
                    err=True,
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
                "NOT READY — fix blocking items, then run `lemma validator check` again.",
                fg="red",
                bold=True,
            ),
            err=True,
        )
        finish_cli_output()
        return 1

    if warn:
        _print_ready_footer(outcome="warn")
        finish_cli_output()
        return 0

    _print_ready_footer(outcome="ok")
    finish_cli_output()
    return 0
