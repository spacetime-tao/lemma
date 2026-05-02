"""Interactive env configuration: merge into ``.env`` so operators avoid hand-editing files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click

from lemma.common.env_file import merge_dotenv

# Subnet default stack (see .env.example and MODELS.md)
CHUTES_OPENAI_BASE_URL = "https://llm.chutes.ai/v1"
CHUTES_DEFAULT_MODEL = "Qwen/Qwen3-32B-TEE"
DEFAULT_SUBTENSOR_CHAIN_ENDPOINT = "wss://entrypoint-finney.opentensor.ai:443"


def _require_secret(prompt: str) -> str:
    key = click.prompt(prompt, hide_input=True).strip()
    if not key:
        raise click.UsageError("Value is required.")
    return key


def collect_chain_updates() -> dict[str, str]:
    click.echo("Chain + wallet names (must match coldkeys/hotkeys you created with btcli).")
    netuid = click.prompt("NETUID", type=int)
    network = click.prompt("SUBTENSOR_NETWORK", default="finney", show_default=True)
    endpoint = click.prompt(
        "SUBTENSOR_CHAIN_ENDPOINT",
        default=DEFAULT_SUBTENSOR_CHAIN_ENDPOINT,
        show_default=True,
    ).strip()
    cold = click.prompt("BT_WALLET_COLD (cold wallet name)", default="default", show_default=True).strip()
    hot = click.prompt("BT_WALLET_HOT (hotkey name)", default="default", show_default=True).strip()
    return {
        "NETUID": str(netuid),
        "SUBTENSOR_NETWORK": network,
        "SUBTENSOR_CHAIN_ENDPOINT": endpoint,
        "BT_WALLET_COLD": cold,
        "BT_WALLET_HOT": hot,
    }


def collect_axon_updates() -> dict[str, str]:
    port = click.prompt("AXON_PORT (miners: validators connect here)", default=8091, type=int)
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
    click.echo(f"--- {label} ---")
    merge_dotenv(path, collect())


def run_setup(env_path: Path, role: str) -> None:
    click.echo(f"Lemma writes configuration to {env_path} (no manual file editing).")
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
    click.echo("Done. Remaining manual steps: on-chain registration / funding (btcli).")
    click.echo("Validators: run `bash scripts/prebuild_lean_image.sh` before first run if the image is not built yet.")
