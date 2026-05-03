"""Run the prover once against the same theorem validators would sample at current head.

This is a **manual** check (operator-triggered). The always-on miner solves as soon as validators
forward a synapse — see ``lemma.miner.forward``.
"""

from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import click
from openai import APIConnectionError, APITimeoutError

from lemma.cli.problem_views import echo_problem_card
from lemma.cli.style import finish_cli_output, flush_stdio, stylize
from lemma.common.block_deadline import compute_forward_deadline_and_wait
from lemma.common.config import LemmaSettings
from lemma.common.logging import setup_logging
from lemma.common.problem_seed import (
    blocks_until_challenge_may_change,
    format_next_theorem_countdown,
    resolve_problem_seed,
)
from lemma.common.subtensor import get_subtensor
from lemma.lean.cheats import lake_build_environment_failed
from lemma.lean.verify_runner import run_lean_verify
from lemma.miner.prover import LLMProver
from lemma.problems.factory import get_problem_source
from lemma.protocol import LemmaChallenge
from lemma.reasoning.format import format_reasoning_steps


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes")


def resolve_try_prover_use_docker(
    *,
    verify: bool,
    explicit_use_docker: bool | None,
    base_use_docker: bool = True,
    allow_host_lean: bool = False,
) -> bool:
    """How ``try-prover`` runs Lean when ``--verify`` is set.

    **Defaults match validators:** use Docker when ``LEMMA_USE_DOCKER`` is true (the usual subnet setup).
    Host ``lake`` is opt-in (``--host-lean`` or ``LEMMA_TRY_PROVER_HOST_VERIFY=1``) for a faster dev path.

    ``base_use_docker`` is ``LemmaSettings.lean_use_docker`` from ``.env``.

    Validators/miners are unchanged — this only applies to ``lemma try-prover``.
    """
    if explicit_use_docker is not None:
        return explicit_use_docker
    if not verify:
        return base_use_docker
    if _env_truthy("LEMMA_TRY_PROVER_DOCKER_VERIFY"):
        return True
    if _env_truthy("LEMMA_TRY_PROVER_HOST_VERIFY") and allow_host_lean:
        return False
    return base_use_docker


def assert_host_lean_cli_allowed(settings: LemmaSettings, host_lean: bool) -> None:
    """``lemma verify --host-lean`` — same policy as try-prover (opt-in)."""
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException(
            "Host Lean is disabled. Use Docker (default) to match validators. "
            "Set LEMMA_ALLOW_HOST_LEAN=1 in `.env` for local debugging, then use --host-lean."
        )


def assert_try_prover_host_lean_allowed(settings: LemmaSettings, *, verify: bool, host_lean: bool) -> None:
    """Raise ClickException if CLI/env requests host Lean without ``LEMMA_ALLOW_HOST_LEAN``."""
    if not verify:
        return
    if host_lean and not settings.allow_host_lean:
        raise click.ClickException(
            "Host Lean is disabled (subnet default is Docker). "
            "Set LEMMA_ALLOW_HOST_LEAN=1 in `.env` for local debugging only, then retry `--host-lean`."
        )
    if _env_truthy("LEMMA_TRY_PROVER_HOST_VERIFY") and not settings.allow_host_lean:
        raise click.ClickException(
            "LEMMA_TRY_PROVER_HOST_VERIFY is set but host Lean is not enabled. "
            "Set LEMMA_ALLOW_HOST_LEAN=1 in `.env`, or unset LEMMA_TRY_PROVER_HOST_VERIFY to use Docker."
        )


def resolve_try_prover_workspace_cache(settings: LemmaSettings) -> Path | None:
    """Warm-cache directory for ``try-prover --verify``: env wins; else ``~/.cache/lemma-lean-workspace``."""
    if settings.lean_verify_workspace_cache_dir is not None:
        return Path(settings.lean_verify_workspace_cache_dir)
    if _env_truthy("LEMMA_TRY_PROVER_NO_WORKSPACE_CACHE"):
        return None
    base = os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    return Path(base) / "lemma-lean-workspace"


def _echo_prover_api_error_hints(exc: BaseException) -> None:
    """Short hints when the gateway rejects the request (esp. wrong model slug)."""
    raw = str(exc)
    low = raw.lower()
    if "404" in raw or "model not found" in low or "not found" in low and "model" in low:
        click.echo(
            stylize(
                "Tip: Your gateway rejected the model id (404). Set PROVER_MODEL to a name that "
                "OPENAI_BASE_URL actually serves — Chutes and other proxies only expose specific slugs "
                "(check their model list; preview vs stable names differ).",
                dim=True,
            ),
            err=True,
        )


def _run_try_prover_session(
    settings: LemmaSettings,
    *,
    verify: bool,
    block: int | None,
    lean_use_docker: bool | None = None,
) -> int:
    """Run chain setup, LLM, optional Lean verify; return process exit code."""
    use_docker = resolve_try_prover_use_docker(
        verify=verify,
        explicit_use_docker=lean_use_docker,
        base_use_docker=settings.lean_use_docker,
        allow_host_lean=settings.allow_host_lean,
    )
    setup_logging(settings.log_level)
    from lemma import __version__

    try:
        subtensor = get_subtensor(settings)
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(
            f"Chain RPC required (same as `lemma status`): {e}",
        ) from e

    try:
        head = int(block) if block is not None else int(subtensor.get_current_block())
    except Exception as e:  # noqa: BLE001
        raise click.ClickException(str(e)) from e

    problem_seed, seed_tag = resolve_problem_seed(
        chain_head_block=head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        subtensor=subtensor,
    )
    src = get_problem_source(settings)
    problem = src.sample(seed=problem_seed)
    deadline_block, timeout_s = compute_forward_deadline_and_wait(
        settings=settings,
        subtensor=subtensor,
        cur_block=head,
        seed_tag=seed_tag,
        wait_scale=1.0,
    )
    synapse = LemmaChallenge(
        theorem_id=problem.id,
        theorem_statement=problem.challenge_source(),
        imports=list(problem.imports),
        lean_toolchain=problem.lean_toolchain,
        mathlib_rev=problem.mathlib_rev,
        deadline_unix=int(time.time()) + int(timeout_s),
        deadline_block=deadline_block,
        metronome_id=str(problem_seed),
        timeout=timeout_s,
    )

    click.echo(stylize(f"lemma {__version__} — try-prover", fg="cyan", bold=True))
    click.echo(
        stylize(
            "Stop anytime: Ctrl+C once → exits try-prover and returns you to the shell (exit 130).",
            fg="green",
            bold=True,
        ),
        err=True,
    )
    click.echo(
        stylize(
            "When this command ends (success or failure): you should get your normal shell prompt back. "
            "If the terminal looks stuck with no prompt, press Enter once.",
            fg="green",
        ),
        err=True,
    )
    click.echo(
        stylize(
            "This bills your prover API (Chutes, Anthropic, …) — same as handling one validator forward.",
            fg="yellow",
            bold=True,
        ),
    )
    click.echo(
        stylize(
            f"chain_head_block={head}  problem_seed={problem_seed}  seed_tag={seed_tag}",
            dim=True,
        ),
    )
    llm_budget = float(settings.llm_http_timeout_s)
    _prov_tok = int(settings.prover_max_tokens)
    click.echo("")
    _bt = float(settings.block_time_sec_estimate)
    click.echo(stylize("When mining — time budget on the axon", fg="cyan", bold=True))
    click.echo(
        stylize(
            f"Validator will wait up to {int(timeout_s)}s for your full answer (HTTP) — "
            f"roughly the rest of the current N-block window at ~{_bt:.0f}s/block. "
            f"One LLM call can use up to {llm_budget:.0f}s (LEMMA_LLM_HTTP_TIMEOUT_S); keep that inside the window. "
            f"Prover completion budget: up to {_prov_tok:,} tokens (LEMMA_PROVER_MAX_TOKENS).",
            dim=True,
        ),
    )
    click.echo(
        stylize(
            f"Chain says finish before block {deadline_block} (same window as the countdown below).",
            dim=True,
        ),
    )
    click.echo("")
    click.echo(stylize("Time until the next theorem", fg="cyan", bold=True))
    bl, _ = blocks_until_challenge_may_change(
        chain_head_block=head,
        netuid=settings.netuid,
        mode=settings.problem_seed_mode,
        quantize_blocks=settings.problem_seed_quantize_blocks,
        seed_tag=seed_tag,
        subtensor=subtensor,
    )
    _countdown = format_next_theorem_countdown(
        chain_head_block=head,
        blocks_until_theorem_changes=bl,
        seconds_per_block=_bt,
    )
    click.echo(stylize(_countdown, fg="yellow", bold=True))
    click.echo(
        stylize(
            f"Times are estimates from LEMMA_BLOCK_TIME_SEC_ESTIMATE ({_bt:.0f}s/block).",
            dim=True,
        ),
    )
    click.echo("")
    echo_problem_card(
        problem,
        heading="Theorem",
        settings=settings,
        synapse_timeout_s=timeout_s,
        show_timeout_help=True,
    )
    if verify and use_docker:
        nm = (settings.lean_sandbox_network or "none").strip().lower()
        if nm in ("none", ""):
            click.echo(
                stylize(
                    "Lean verify — sandbox network is off (LEAN_SANDBOX_NETWORK defaults to none). "
                    "Docker `lake` often needs GitHub for Mathlib on a cold workspace — set "
                    "LEAN_SANDBOX_NETWORK=bridge in `.env` for local `--verify`, or bake/cache deps in the image.",
                    fg="yellow",
                    bold=True,
                ),
            )
            click.echo("")
    click.echo(
        stylize(
            "Calling your prover LLM (no axon / no other miners). Long runs are normal on medium/hard; "
            "transient HTTP errors are retried a few times automatically.",
            dim=True,
        ),
    )
    click.echo(
        stylize(
            "While waiting there is no extra output until the model responds — this is normal. "
            "Press Ctrl+C once to abort (HTTP retries can take several minutes on connection errors).",
            fg="yellow",
        ),
    )

    prover = LLMProver(settings)

    async def _solve() -> int:
        try:
            trace, proof, steps = await prover.solve(synapse)
        except (APIConnectionError, APITimeoutError):
            click.echo(
                stylize(
                    "LLM request failed after automatic retries — connection dropped or read timed out "
                    "(common on long Chutes generations).\n",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )
            click.echo(
                stylize(
                    "Try: increase LEMMA_PROVER_LLM_RETRY_ATTEMPTS on 429 / saturation; "
                    "raise LEMMA_LLM_HTTP_TIMEOUT_S if streams drop; keep timeout within forward wait "
                    "(LEMMA_BLOCK_TIME / FORWARD_WAIT_*); or retry when the API is less loaded.",
                    dim=True,
                ),
                err=True,
            )
            click.echo(
                stylize("try-prover: stopped — LLM transport error (exit 2)", fg="red", bold=True),
                err=True,
            )
            flush_stdio()
            return 2
        except Exception as e:  # noqa: BLE001
            click.echo(stylize(f"Prover error: {e}", fg="red", bold=True), err=True)
            _echo_prover_api_error_hints(e)
            click.echo(
                stylize("try-prover: stopped — prover API error (exit 1)", fg="red", bold=True),
                err=True,
            )
            flush_stdio()
            return 1

        click.echo(stylize("— Reasoning (informal) —", fg="cyan", bold=True))
        if steps:
            click.echo(format_reasoning_steps(steps))
        else:
            click.echo(trace or "(empty)")
        if not steps and not (trace or "").strip() and (proof or "").strip():
            click.echo(
                stylize(
                    "Note: the model returned proof_script but no reasoning_steps / reasoning_trace — "
                    "informal steps are empty; your judge still sees the proof text.",
                    dim=True,
                ),
            )
        click.echo("")
        click.echo(stylize("— proof_script (Submission.lean) —", fg="cyan", bold=True))
        click.echo(proof or "(empty)")
        click.echo("")

        etext = format_reasoning_steps(steps) if steps else (trace or "")
        click.echo(stylize(f"(effective reasoning chars for judge: {len(etext)})", dim=True))

        lean_ok: bool | None = None
        if verify and (proof or "").strip():
            ws_cache = resolve_try_prover_workspace_cache(settings)
            eff_settings = settings.model_copy(
                update={
                    "lean_use_docker": use_docker,
                    "lean_verify_workspace_cache_dir": ws_cache,
                },
            )
            click.echo("")
            if ws_cache is not None:
                click.echo(
                    stylize(
                        f"Lean workspace cache: {ws_cache}  "
                        f"(override LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR; disable default: "
                        f"LEMMA_TRY_PROVER_NO_WORKSPACE_CACHE=1)",
                        dim=True,
                    ),
                )
            remote_u = (settings.lean_verify_remote_url or "").strip()
            if remote_u:
                click.echo(
                    stylize(
                        f"Lean verify — remote worker `{remote_u}` (POST /verify). "
                        "Unset LEMMA_LEAN_VERIFY_REMOTE_URL to verify locally.",
                        fg="cyan",
                    ),
                )
            elif not use_docker:
                click.echo(
                    stylize(
                        "Lean verify — host `lake` (opt‑in; warm Mathlib can be fast). "
                        "Default path is Docker — same as validators when LEMMA_USE_DOCKER=1.",
                        fg="cyan",
                    ),
                )
            else:
                _dw = (settings.lemma_lean_docker_worker or "").strip()
                if _dw:
                    click.echo(
                        stylize(
                            f"Lean Docker — `docker exec` into `{_dw}` (set in `.env` as LEMMA_LEAN_DOCKER_WORKER).",
                            fg="cyan",
                        ),
                    )
                else:
                    click.echo(
                        stylize(
                            "Lean Docker — new container per verify (slower). For exec-based verify set "
                            "LEMMA_LEAN_DOCKER_WORKER in `.env` and run `scripts/start_lean_docker_worker.sh`.",
                            dim=True,
                        ),
                    )
            click.echo(
                stylize(
                    "Lean verify may take many minutes on a cold Mathlib build — Ctrl+C aborts and exits.",
                    dim=True,
                ),
            )
            click.echo(
                stylize(
                    "— Lean verify (same kernel check as validators; "
                    + ("remote POST /verify when LEMMA_LEAN_VERIFY_REMOTE_URL is set; " if remote_u else "")
                    + "not on-chain scoring) —",
                    fg="cyan",
                    bold=True,
                ),
            )
            vr = await asyncio.to_thread(
                run_lean_verify,
                eff_settings,
                verify_timeout_s=settings.lean_verify_timeout_s,
                problem=problem,
                proof_script=proof,
            )
            lean_ok = bool(vr.passed)
            if vr.passed:
                click.echo(stylize("PASS", fg="green") + f"  ({vr.build_seconds:.2f}s)")
            else:
                click.echo(stylize(f"FAIL  {vr.reason}", fg="red", bold=True))
                if vr.stderr_tail:
                    click.echo(vr.stderr_tail[-16000:])
                    click.echo("")
                tail = (vr.stderr_tail or "") + (vr.stdout_tail or "")
                tail_lower = tail.lower()
                if lake_build_environment_failed(tail):
                    click.echo(
                        stylize(
                            "Hint: `lake` could not reach the network (e.g. GitHub for Mathlib). "
                            "Default Docker sandbox uses no internet (LEAN_SANDBOX_NETWORK=none). "
                            "For local verify, set LEAN_SANDBOX_NETWORK=bridge in `.env`, or use an image "
                            "that already has dependencies baked in.",
                            dim=True,
                        ),
                        err=True,
                    )
                elif (
                    "no previous manifest" in tail_lower
                    or "creating one from scratch" in tail_lower
                    or "post-update hooks" in tail_lower
                ):
                    click.echo(
                        stylize(
                            "Hint: Mathlib/Lake cold start or hooks — often **not** a wrong `rfl` proof. "
                            "First builds download/build a lot; Docker default may hit timeout or no-network. "
                            "Try: raise LEAN_VERIFY_TIMEOUT_S; use `scripts/prebuild_lean_image.sh` + "
                            "LEAN_SANDBOX_IMAGE with warmed `.lake`; LEAN_SANDBOX_NETWORK=bridge if GitHub "
                            "must be reached from the container.",
                            dim=True,
                        ),
                        err=True,
                    )
        elif verify:
            click.echo("")
            click.echo(
                stylize(
                    "— Lean verify (local) — skipped (empty proof_script)",
                    fg="yellow",
                ),
                err=True,
            )

        click.echo("")
        if lean_ok is True:
            click.echo(stylize("try-prover: finished — LLM OK, Lean verify PASS (exit 0)", fg="green"))
            return 0
        if lean_ok is False:
            click.echo(
                stylize(
                    "try-prover: finished — Lean verify FAIL (exit 1). "
                    "Fix the proof or Mathlib setup; ensure Docker can run the sandbox image "
                    "or use --host-lean for host lake.",
                    fg="red",
                    bold=True,
                ),
                err=True,
            )
            return 1
        if verify:
            click.echo(stylize("try-prover: finished — LLM OK, nothing to compile (exit 0)", fg="green"))
            return 0
        click.echo(
            stylize(
                "try-prover: finished — LLM OK (exit 0). Lean was not run; run "
                "`lemma try-prover --verify` to compile Submission.lean locally.",
                fg="green",
            ),
        )
        return 0

    return asyncio.run(_solve())


def run_try_prover(
    settings: LemmaSettings,
    *,
    verify: bool,
    block: int | None,
    prover_llm_retry_attempts: int | None = None,
    lean_use_docker: bool | None = None,
) -> None:
    """Load current (or --block) seed, call LLM prover, print trace + proof; optional Lean verify."""
    if prover_llm_retry_attempts is not None:
        settings = settings.model_copy(update={"prover_llm_retry_attempts": prover_llm_retry_attempts})
    exit_code = 1
    try:
        exit_code = _run_try_prover_session(
            settings,
            verify=verify,
            block=block,
            lean_use_docker=lean_use_docker,
        )
    except KeyboardInterrupt:
        click.echo("")
        click.echo(
            stylize(
                "try-prover: interrupted (Ctrl+C) — exit 130. "
                "You are back at the shell; if the prompt did not redraw, press Enter once.",
                fg="yellow",
                bold=True,
            ),
            err=True,
        )
        exit_code = 130

    # Exit 0: the green "try-prover: finished …" line above is enough; avoid extra ANSI here.
    # Non-zero: plain stderr line (no stylize) so we do not add SGR after error output.
    if exit_code != 130 and exit_code != 0:
        click.echo("try-prover: done (non-zero exit). See messages above.", err=True)
    # Reset streams + /dev/tty (see finish_cli_output) — IDE terminals often need the latter for the prompt.
    finish_cli_output()
    if exit_code != 0:
        raise SystemExit(exit_code)
