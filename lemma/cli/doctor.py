from __future__ import annotations

from pathlib import Path

import click

from lemma.cli.style import finish_cli_output, stylize
from lemma.common.config import LemmaSettings


def _present(value: str | None) -> bool:
    return bool(value and str(value).strip())


def _api_lines(settings: LemmaSettings) -> tuple[list[str], bool]:
    lines: list[str] = []
    ok_all = True
    prover_provider = (settings.prover_provider or "anthropic").lower()

    tasks: list[tuple[str, str]] = []
    if prover_provider == "openai":
        tasks.append(("Prover", "openai"))
    elif prover_provider == "anthropic":
        tasks.append(("Prover", "anthropic"))
    else:
        lines.append(f"INFO prover: PROVER_PROVIDER={prover_provider!r}")

    for role, kind in tasks:
        if kind == "openai":
            ok = _present(settings.prover_openai_api_key_resolved())
            key_hint = (
                "PROVER_OPENAI_API_KEY"
                if settings.prover_openai_api_key and str(settings.prover_openai_api_key).strip()
                else "OPENAI_API_KEY (fallback)"
            )
            ok_all = ok_all and ok
            tag = "OK" if ok else "WARN"
            suffix = f"{key_hint} present (hidden)" if ok else f"{key_hint} missing"
            lines.append(f"{tag} {role} (OpenAI-compatible): {suffix}")
        else:
            ok = _present(settings.anthropic_api_key)
            ok_all = ok_all and ok
            tag = "OK" if ok else "WARN"
            suffix = "ANTHROPIC_API_KEY present (hidden)" if ok else "ANTHROPIC_API_KEY missing"
            lines.append(f"{tag} {role} (Anthropic): {suffix}")

    return lines, ok_all


def _chain_snapshot(settings: LemmaSettings) -> tuple[int | None, float | None, Exception | None]:
    try:
        from lemma.common.block_deadline import forward_wait_at_chain_head
        from lemma.common.subtensor import get_subtensor

        subtensor = get_subtensor(settings)
        head = int(subtensor.get_current_block())
        _, _, _, forward_wait = forward_wait_at_chain_head(
            settings=settings,
            subtensor=subtensor,
            chain_head_block=head,
        )
        return head, float(forward_wait), None
    except Exception as exc:  # noqa: BLE001
        return None, None, exc


def run_doctor() -> int:
    ok = True
    keys_ok = True
    root = Path.cwd()
    click.echo(stylize("\nlemma doctor", fg="cyan", bold=True))
    click.echo(stylize("-" * 42, dim=True))

    click.echo(stylize("\n1  Environment", fg="cyan", bold=True))
    if (root / ".venv").is_dir():
        click.echo(stylize("   OK", fg="green") + "    .venv present (core Lemma uv env)")
    else:
        click.echo(
            stylize("   MISS", fg="red")
            + "  .venv - run from the core Lemma repo after `uv sync --extra btcli`",
            err=True,
        )
        ok = False

    try:
        settings = LemmaSettings()
    except Exception as exc:  # noqa: BLE001
        click.echo(stylize("CONFIG ERROR: ", fg="red") + str(exc), err=True)
        finish_cli_output()
        return 1

    click.echo(stylize("\n2  Configuration (.env)", fg="cyan", bold=True))
    click.echo(
        stylize("   OK", fg="green")
        + f"    NETUID={settings.netuid}  problem_source={settings.problem_source}",
    )
    key_lines, keys_ok = _api_lines(settings)
    for line in key_lines:
        click.echo(f"   {line}")
    click.echo(
        stylize(
            "   (Keys above follow active config - `.env` wins over shell unless LEMMA_PREFER_PROCESS_ENV=1.)",
            dim=True,
        ),
    )

    prover_provider = (settings.prover_provider or "anthropic").lower()
    if prover_provider == "openai":
        model = settings.prover_model or settings.openai_model
        base_url = settings.prover_openai_base_url_resolved()
        click.echo(
            stylize("   .", dim=True)
            + f"    Prover  model={model!r} @ {base_url!r}",
        )
    elif prover_provider == "anthropic":
        model = settings.prover_model or settings.anthropic_model
        click.echo(stylize("   .", dim=True) + f"    Prover  model={model!r}")

    chain_head, forward_wait, chain_error = _chain_snapshot(settings)

    click.echo(stylize("\n3  Timeouts (vs validator forward window)", fg="cyan", bold=True))
    if forward_wait is not None:
        max_wait = float(settings.forward_wait_max_s)
        llm_timeout = float(settings.llm_http_timeout_s)
        if llm_timeout > max_wait + 0.01:
            click.echo(
                stylize(
                    "   WARN  LEMMA_LLM_HTTP_TIMEOUT_S exceeds LEMMA_FORWARD_WAIT_MAX_S - "
                    "prover cannot finish inside any validator axon wait window.",
                    fg="yellow",
                ),
                err=True,
            )
        elif llm_timeout > forward_wait + 0.01:
            click.echo(
                stylize(
                    f"   OK    LLM timeout {llm_timeout:.0f}s > this-head forward wait ~{forward_wait:.0f}s "
                    "(normal near a seed edge; lower LLM timeout only if miners time out late-window).",
                    dim=True,
                ),
            )
        else:
            click.echo(
                stylize(f"   OK    LLM timeout fits this-head forward wait (~{forward_wait:.0f}s)", dim=True),
            )
    elif settings.llm_http_timeout_s > settings.forward_wait_max_s + 0.01:
        click.echo(
            stylize(
                "   WARN  LEMMA_LLM_HTTP_TIMEOUT_S > LEMMA_FORWARD_WAIT_MAX_S - "
                "cannot fit any round's forward wait.",
                fg="yellow",
            ),
            err=True,
        )
    else:
        click.echo(stylize("   INFO  Connect chain RPC for a block-accurate timeout check.", dim=True))

    if not (settings.judge_profile_expected_sha256 or "").strip():
        click.echo(
            stylize(
                "   Tip   Validators: set LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED "
                "(`lemma config subnet-pins`; copy from `lemma config meta --raw`).",
                dim=True,
            ),
        )

    click.echo(stylize("\n4  Chain RPC", fg="cyan", bold=True))
    if chain_head is not None:
        click.echo(stylize("   OK", fg="green") + f"    head_block={chain_head}")
    else:
        click.echo(stylize("   SKIP", fg="yellow") + f"  (offline OK): {chain_error}")

    click.echo(
        stylize(
            "\n5  Next commands\n"
            "     lemma status            - current theorem window\n"
            "     lemma miner check       - miner readiness\n"
            "     lemma validator check   - validator readiness\n",
            dim=True,
        ),
        nl=False,
    )

    if not ok:
        finish_cli_output()
        return 1
    if not keys_ok:
        click.echo(
            stylize(
                "\nSummary: WARN - add missing prover keys before mining or preview.",
                fg="yellow",
            ),
            err=True,
        )
    else:
        click.echo(stylize("\nSummary: OK", fg="green"))
    finish_cli_output()
    return 0
