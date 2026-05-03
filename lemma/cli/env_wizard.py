"""Interactive env configuration: merge into ``.env`` so operators avoid hand-editing files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click

from lemma.cli.style import stylize
from lemma.common.config import CANONICAL_JUDGE_OPENAI_MODEL, LemmaSettings
from lemma.common.env_file import merge_dotenv

# Subnet default stack (see .env.example and MODELS.md)
CHUTES_OPENAI_BASE_URL = "https://llm.chutes.ai/v1"
CHUTES_DEFAULT_MODEL = CANONICAL_JUDGE_OPENAI_MODEL
# Matches LemmaSettings.anthropic_model default (prover falls back if PROVER_MODEL unset).
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

# Official entrypoints (Bittensor docs — mainnet vs testnet).
CHAIN_ENDPOINT_FINNEY = "wss://entrypoint-finney.opentensor.ai:443"
CHAIN_ENDPOINT_TEST = "wss://test.finney.opentensor.ai:443"
DEFAULT_SUBTENSOR_CHAIN_ENDPOINT = CHAIN_ENDPOINT_FINNEY


def _require_secret(prompt: str) -> str:
    key = click.prompt(prompt, hide_input=True).strip()
    if not key:
        raise click.UsageError("Value is required.")
    return key


def collect_chain_updates() -> dict[str, str]:
    click.echo(
        stylize("Chain", fg="cyan", bold=True)
        + stylize(" — wallet names must match ", dim=True)
        + stylize("btcli", fg="yellow")
        + stylize(" coldkeys / hotkeys.\n", dim=True),
        nl=False,
    )
    netuid = click.prompt(stylize("NETUID", fg="green"), type=int)

    preset = click.prompt(
        stylize("Network", fg="green"),
        type=click.Choice(["finney", "test", "custom"], case_sensitive=False),
        default="finney",
    )
    preset_l = preset.strip().lower()
    if preset_l == "finney":
        network, endpoint = "finney", CHAIN_ENDPOINT_FINNEY
    elif preset_l == "test":
        network, endpoint = "test", CHAIN_ENDPOINT_TEST
    else:
        click.echo(stylize("Custom RPC — paste values from your operator.\n", dim=True))
        network = click.prompt(
            stylize("SUBTENSOR_NETWORK", fg="green"),
            default="finney",
            show_default=True,
        ).strip()
        endpoint = click.prompt(
            stylize("SUBTENSOR_CHAIN_ENDPOINT", fg="green"),
            default=DEFAULT_SUBTENSOR_CHAIN_ENDPOINT,
            show_default=True,
        ).strip()

    click.echo(
        stylize(f"→ {network}", fg="cyan")
        + stylize("  ", dim=True)
        + stylize(endpoint, dim=True)
        + "\n",
        nl=False,
    )

    cold = click.prompt(
        stylize("Cold wallet name", fg="green") + stylize(" (BT_WALLET_COLD)", dim=True),
        default="default",
        show_default=True,
    ).strip()
    hot = click.prompt(
        stylize("Hotkey name", fg="green") + stylize(" (BT_WALLET_HOT)", dim=True),
        default="default",
        show_default=True,
    ).strip()
    return {
        "NETUID": str(netuid),
        "SUBTENSOR_NETWORK": network,
        "SUBTENSOR_CHAIN_ENDPOINT": endpoint,
        "BT_WALLET_COLD": cold,
        "BT_WALLET_HOT": hot,
    }


def collect_axon_updates() -> dict[str, str]:
    click.echo(
        stylize(
            "TCP port for the miner axon. Validators connect to ",
            dim=True,
        )
        + stylize("your_public_ip:AXON_PORT", fg="yellow")
        + stylize(". Default 8091 is fine unless that port is taken.\n", dim=True),
        nl=False,
    )
    port = click.prompt(
        stylize("AXON_PORT", fg="green") + stylize("  [Enter = 8091]", dim=True),
        default=8091,
        type=int,
        show_default=True,
    )
    click.echo(
        stylize("→ will write ", dim=True)
        + stylize(f"AXON_PORT={port}\n", fg="green"),
        nl=False,
    )
    return {"AXON_PORT": str(port)}


def collect_lean_image_updates() -> dict[str, str]:
    """Subnet Lean sandbox tag — fixed; build locally with ``scripts/prebuild_lean_image.sh``."""
    img = "lemma/lean-sandbox:latest"
    click.echo(
        stylize(
            "Validators check miners’ proofs inside this Docker image (everyone uses the same tag).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize("Build it once from the repo root: ", dim=True)
        + stylize("bash scripts/prebuild_lean_image.sh", fg="yellow")
        + stylize("  →  writes ", dim=True)
        + stylize(img, fg="green")
        + stylize(" locally.\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(f"→ writing LEAN_SANDBOX_IMAGE={img} to `.env`\n", dim=True),
        nl=False,
    )
    return {"LEAN_SANDBOX_IMAGE": img}


def _backend_choice(role_label: str) -> str:
    click.echo(
        stylize(
            f"{role_label} — pick an API. ",
            dim=True,
        )
        + stylize("chutes", fg="yellow")
        + stylize(" matches the subnet’s recommended stack (https://llm.chutes.ai/v1).\n", dim=True),
        nl=False,
    )
    return click.prompt(
        stylize("Backend", fg="green"),
        type=click.Choice(["chutes", "anthropic", "custom_openai"], case_sensitive=False),
        default="chutes",
    )


def collect_judge_updates() -> dict[str, str]:
    backend = _backend_choice("Judge (scores miner proofs + traces)").lower()
    updates: dict[str, str]
    if backend == "chutes":
        key = _require_secret("Chutes API key (OpenAI-compatible)")
        updates = {
            "JUDGE_PROVIDER": "chutes",
            "OPENAI_API_KEY": key,
            "OPENAI_BASE_URL": CHUTES_OPENAI_BASE_URL,
            "OPENAI_MODEL": CHUTES_DEFAULT_MODEL,
        }
        click.echo(
            stylize(
                "→ will write judge settings + API key to .env (key not printed). "
                f"Model  {CHUTES_DEFAULT_MODEL}  (change later: `lemma configure judge`)\n",
                dim=True,
            ),
            nl=False,
        )
    elif backend == "anthropic":
        key = _require_secret("Anthropic API key")
        updates = {
            "JUDGE_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": key,
        }
    else:
        key = _require_secret("OpenAI-compatible API key")
        click.echo(
            stylize(
                "Gemini (Google AI Studio): OPENAI_BASE_URL\n  ",
                dim=True,
            )
            + stylize("https://generativelanguage.googleapis.com/v1beta/openai/", fg="yellow")
            + stylize(
                "  OPENAI_MODEL = Gemini id (e.g. ",
                dim=True,
            )
            + stylize("gemini-2.0-flash", fg="green")
            + stylize(").\n", dim=True),
            nl=False,
        )
        url = click.prompt(
            "OPENAI_BASE_URL (e.g. https://api.openai.com/v1 or http://127.0.0.1:8000/v1)",
            default="",
            show_default=False,
        ).strip()
        model = click.prompt("OPENAI_MODEL", default="", show_default=False).strip()
        if not url or not model:
            raise click.UsageError("OPENAI_BASE_URL and OPENAI_MODEL are required for custom OpenAI-compatible.")
        updates = {
            "JUDGE_PROVIDER": "openai",
            "OPENAI_API_KEY": key,
            "OPENAI_BASE_URL": url,
            "OPENAI_MODEL": model,
        }
    return updates


def collect_prover_updates() -> dict[str, str]:
    backend = _backend_choice("Prover (writes Submission.lean when you mine)").lower()
    updates: dict[str, str]
    if backend == "chutes":
        key = _require_secret("Chutes API key (prover)")
        click.echo(
            stylize(
                "PROVER_MODEL / PROVER_OPENAI_BASE_URL are miner-only; the judge uses OPENAI_MODEL / OPENAI_BASE_URL "
                "(set via `lemma configure judge`).",
                dim=True,
            )
        )
        model = click.prompt(
            stylize("PROVER_MODEL", fg="green") + stylize(f"  [Enter = {CHUTES_DEFAULT_MODEL}]", dim=True),
            default=CHUTES_DEFAULT_MODEL,
            show_default=True,
        ).strip()
        use_model = model or CHUTES_DEFAULT_MODEL
        updates = {
            "PROVER_PROVIDER": "openai",
            "OPENAI_API_KEY": key,
            "PROVER_OPENAI_BASE_URL": CHUTES_OPENAI_BASE_URL,
            "PROVER_MODEL": use_model,
        }
        click.echo(
            stylize("→ will write prover + key to .env; prover model ", dim=True)
            + stylize(use_model, fg="green")
            + stylize("\n", dim=True),
            nl=False,
        )
    elif backend == "anthropic":
        key = _require_secret("Anthropic API key (prover)")
        model = click.prompt(
            stylize("PROVER_MODEL", fg="green")
            + stylize(f"  [Enter = {DEFAULT_ANTHROPIC_MODEL}]", dim=True),
            default=DEFAULT_ANTHROPIC_MODEL,
            show_default=True,
        ).strip()
        use_model = model or DEFAULT_ANTHROPIC_MODEL
        updates = {
            "PROVER_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": key,
            "PROVER_MODEL": use_model,
        }
        click.echo(
            stylize("→ will write prover + key to .env; prover model ", dim=True)
            + stylize(use_model, fg="green")
            + stylize("\n", dim=True),
            nl=False,
        )
    else:
        key = _require_secret("OpenAI-compatible API key (prover)")
        click.echo(
            stylize(
                "Gemini (Google AI Studio key): set PROVER_OPENAI_BASE_URL to\n  ",
                dim=True,
            )
            + stylize("https://generativelanguage.googleapis.com/v1beta/openai/", fg="yellow")
            + stylize(
                "\n  and PROVER_MODEL to a Gemini id (e.g. ",
                dim=True,
            )
            + stylize("gemini-2.0-flash", fg="green")
            + stylize(
                ", or the exact id from AI Studio). See https://ai.google.dev/gemini-api/docs/openai\n",
                dim=True,
            ),
            nl=False,
        )
        url = click.prompt(
            "PROVER_OPENAI_BASE_URL",
            default="",
            show_default=False,
        ).strip()
        model = click.prompt("PROVER_MODEL", default="", show_default=False).strip()
        if not url or not model:
            raise click.UsageError(
                "PROVER_OPENAI_BASE_URL and PROVER_MODEL are required for custom OpenAI-compatible prover.",
            )
        updates = {
            "PROVER_PROVIDER": "openai",
            "OPENAI_API_KEY": key,
            "PROVER_OPENAI_BASE_URL": url,
            "PROVER_MODEL": model,
        }
    return updates


def collect_prover_retries_updates() -> dict[str, str]:
    """LEMMA_PROVER_LLM_RETRY_ATTEMPTS — transient LLM errors per forward / try-prover."""
    s = LemmaSettings()
    default_n = int(s.prover_llm_retry_attempts)
    click.echo(
        stylize(
            "429 / timeouts / 5xx: exponential backoff between tries. Higher = more patience; "
            "each forward uses more wall-clock (watch validator forward wait).\n",
            dim=True,
        ),
        nl=False,
    )
    n = click.prompt(
        stylize("LEMMA_PROVER_LLM_RETRY_ATTEMPTS", fg="green"),
        default=default_n,
        type=click.IntRange(1, 32),
        show_default=True,
    )
    click.echo(
        stylize(f"→ will write LEMMA_PROVER_LLM_RETRY_ATTEMPTS={n}\n", dim=True),
        nl=False,
    )
    return {"LEMMA_PROVER_LLM_RETRY_ATTEMPTS": str(n)}


def collect_prover_model_updates() -> dict[str, str]:
    """Set only PROVER_MODEL (miner); judges keep OPENAI_MODEL / ANTHROPIC_MODEL."""
    click.echo(
        stylize(
            "This name is sent to your prover API as the model id (miner only). Judges use "
            "OPENAI_MODEL / ANTHROPIC_MODEL instead.",
            dim=True,
        )
    )
    click.echo(
        stylize(
            "How to find an id: on Chutes list models — ",
            dim=True,
        )
        + stylize("curl -sS https://llm.chutes.ai/v1/models | jq '.data[].id'", fg="yellow")
        + stylize(
            " — use the exact ",
            dim=True,
        )
        + stylize("id", fg="green")
        + stylize(" string (same form as OPENAI_MODEL).\n", dim=True),
        nl=False,
    )
    click.echo(
        stylize(
            "Type it at the prompt without quotes (quotes are only needed inside shell scripts; "
            "this wizard writes them into .env for you). Example: ",
            dim=True,
        )
        + stylize(CANONICAL_JUDGE_OPENAI_MODEL, fg="green")
        + stylize(" (subnet judge) or any strong ", dim=True)
        + stylize("reasoning", fg="green")
        + stylize(" model on Chutes.\n", dim=True)
        + stylize(".\n", dim=True),
        nl=False,
    )
    m = click.prompt(
        stylize("PROVER_MODEL", fg="green"),
        default="",
        show_default=False,
    ).strip()
    if not m:
        raise click.UsageError("PROVER_MODEL cannot be empty.")
    return {"PROVER_MODEL": m}


def collect_subnet_pin_updates(settings: LemmaSettings) -> dict[str, str]:
    """Expected-hash pins matching **current** `lemma meta` (same judge env + same generated registry code)."""
    from lemma.judge.profile import judge_profile_sha256
    from lemma.problems.generated import generated_registry_sha256

    out: dict[str, str] = {"JUDGE_PROFILE_SHA256_EXPECTED": judge_profile_sha256(settings).strip().lower()}
    if (settings.problem_source or "").strip().lower() == "generated":
        out["LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED"] = generated_registry_sha256().strip().lower()
    return out


def merge_prompted(path: Path, label: str, collect: Callable[[], dict[str, str]]) -> None:
    click.echo("")
    click.echo(stylize(f"── {label} ──", fg="cyan", bold=True))
    merge_dotenv(path, collect())


def run_setup(env_path: Path, role: str) -> None:
    click.echo(stylize("\nLemma setup\n", fg="cyan", bold=True), nl=False)
    click.echo(
        stylize("Writes answers into ", dim=True)
        + stylize(str(env_path), fg="yellow")
        + stylize(" as each answer is merged — safe to re-run if you mistype.\n", dim=True),
        nl=False,
    )
    merge_prompted(env_path, "Chain + wallets", collect_chain_updates)
    if role == "miner":
        merge_prompted(env_path, "Miner — prover LLM", collect_prover_updates)
        merge_prompted(env_path, "Miner — axon", collect_axon_updates)
    elif role == "validator":
        merge_prompted(env_path, "Validator — judge", collect_judge_updates)
        merge_prompted(env_path, "Validator — Lean Docker image", collect_lean_image_updates)
    else:
        merge_prompted(env_path, "Miner — prover LLM", collect_prover_updates)
        merge_prompted(env_path, "Miner — axon", collect_axon_updates)
        merge_prompted(env_path, "Validator — judge", collect_judge_updates)
        merge_prompted(env_path, "Validator — Lean Docker image", collect_lean_image_updates)

    click.echo("")
    click.echo(stylize("── Done ──", fg="green", bold=True))
    click.echo(
        stylize("  • Register / fund hotkeys with ", dim=True)
        + stylize("btcli", fg="yellow")
        + stylize(" as needed.\n", dim=True),
        nl=False,
    )
    if role in ("validator", "both"):
        click.echo(
            stylize("  • Validator: build image → ", dim=True)
            + stylize("bash scripts/prebuild_lean_image.sh", fg="yellow")
            + stylize("  then  ", dim=True)
            + stylize("lemma validator-check", fg="green")
            + stylize("  before  ", dim=True)
            + stylize("lemma validator", fg="green")
            + stylize(".\n", dim=True),
            nl=False,
        )
    if role in ("miner", "both"):
        click.echo(
            stylize("  • Miner: open ", dim=True)
            + stylize("AXON_PORT", fg="yellow")
            + stylize(" to the internet; check with ", dim=True)
            + stylize("lemma miner-dry", fg="green")
            + stylize(".\n", dim=True),
            nl=False,
        )
