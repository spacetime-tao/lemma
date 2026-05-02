"""Interactive env configuration: merge into ``.env`` so operators avoid hand-editing files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click

from lemma.cli.style import stylize
from lemma.common.env_file import merge_dotenv

# Subnet default stack (see .env.example and MODELS.md)
CHUTES_OPENAI_BASE_URL = "https://llm.chutes.ai/v1"
CHUTES_DEFAULT_MODEL = "Qwen/Qwen3-32B-TEE"

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
        stylize("Validators reach your miner at ", dim=True)
        + stylize("public_ip:AXON_PORT", fg="yellow")
        + stylize(". Press Enter to keep the default port.\n", dim=True),
        nl=False,
    )
    port = click.prompt(
        stylize("AXON_PORT", fg="green") + stylize("  [Enter = 8091]", dim=True),
        default=8091,
        type=int,
        show_default=True,
    )
    return {"AXON_PORT": str(port)}


def collect_lean_image_updates() -> dict[str, str]:
    click.echo(
        "Lean sandbox Docker image (run `bash scripts/prebuild_lean_image.sh` first; "
        "it tags `lemma/lean-sandbox:latest`)."
    )
    img = click.prompt(
        "LEAN_SANDBOX_IMAGE",
        default="lemma/lean-sandbox:latest",
        show_default=True,
    ).strip()
    return {"LEAN_SANDBOX_IMAGE": img}


def _backend_choice() -> str:
    click.echo(
        "Inference backend — Chutes (https://llm.chutes.ai/v1) is recommended for this subnet; "
        "others work as secondary options."
    )
    return click.prompt(
        "Backend",
        type=click.Choice(["chutes", "anthropic", "custom_openai"], case_sensitive=False),
        default="chutes",
    )


def collect_judge_updates() -> dict[str, str]:
    backend = _backend_choice().lower()
    updates: dict[str, str]
    if backend == "chutes":
        key = _require_secret("Chutes API key (OpenAI-compatible)")
        updates = {
            "JUDGE_PROVIDER": "openai",
            "OPENAI_API_KEY": key,
            "OPENAI_BASE_URL": CHUTES_OPENAI_BASE_URL,
            "OPENAI_MODEL": CHUTES_DEFAULT_MODEL,
        }
    elif backend == "anthropic":
        key = _require_secret("Anthropic API key")
        updates = {
            "JUDGE_PROVIDER": "anthropic",
            "ANTHROPIC_API_KEY": key,
        }
    else:
        key = _require_secret("OpenAI-compatible API key")
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
    backend = _backend_choice().lower()
    updates: dict[str, str]
    if backend == "chutes":
        key = _require_secret("Chutes API key (prover)")
        updates = {
            "PROVER_PROVIDER": "openai",
            "OPENAI_API_KEY": key,
            "OPENAI_BASE_URL": CHUTES_OPENAI_BASE_URL,
            "OPENAI_MODEL": CHUTES_DEFAULT_MODEL,
        }
    elif backend == "anthropic":
        key = _require_secret("Anthropic API key (prover)")
        updates = {"PROVER_PROVIDER": "anthropic", "ANTHROPIC_API_KEY": key}
    else:
        key = _require_secret("OpenAI-compatible API key (prover)")
        url = click.prompt(
            "OPENAI_BASE_URL",
            default="",
            show_default=False,
        ).strip()
        model = click.prompt("OPENAI_MODEL", default="", show_default=False).strip()
        if not url or not model:
            raise click.UsageError("OPENAI_BASE_URL and OPENAI_MODEL are required for custom OpenAI-compatible.")
        updates = {
            "PROVER_PROVIDER": "openai",
            "OPENAI_API_KEY": key,
            "OPENAI_BASE_URL": url,
            "OPENAI_MODEL": model,
        }
    return updates


def merge_prompted(path: Path, label: str, collect: Callable[[], dict[str, str]]) -> None:
    click.echo(stylize(f"— {label} —", fg="cyan", bold=True))
    merge_dotenv(path, collect())


def run_setup(env_path: Path, role: str) -> None:
    click.echo(
        stylize("Writing ", dim=True)
        + stylize(str(env_path), fg="yellow")
        + stylize(" (merged prompts; no hand-editing required).\n", dim=True),
        nl=False,
    )
    merge_prompted(env_path, "Chain + wallets", collect_chain_updates)
    if role == "miner":
        merge_prompted(env_path, "Miner — prover LLM", collect_prover_updates)
        merge_prompted(env_path, "Miner — axon", collect_axon_updates)
    elif role == "validator":
        merge_prompted(env_path, "Validator — judge", collect_judge_updates)
        merge_prompted(env_path, "Validator — Lean image", collect_lean_image_updates)
    else:
        merge_prompted(env_path, "Miner — prover LLM", collect_prover_updates)
        merge_prompted(env_path, "Miner — axon", collect_axon_updates)
        merge_prompted(env_path, "Validator — judge", collect_judge_updates)
        merge_prompted(env_path, "Validator — Lean image", collect_lean_image_updates)

    click.echo("")
    click.echo(
        stylize("Done.", fg="green")
        + stylize(" Register / fund with ", dim=True)
        + stylize("btcli", fg="yellow")
        + stylize(". Validators: build Lean image first → ", dim=True)
        + stylize("bash scripts/prebuild_lean_image.sh", fg="yellow"),
    )
