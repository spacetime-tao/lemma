"""Interactive env configuration: merge into ``.env`` so operators avoid hand-editing files."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import click

from lemma.cli.env_file import merge_dotenv
from lemma.cli.style import stylize
from lemma.common.config import CANONICAL_JUDGE_OPENAI_MODEL, LemmaSettings

# Default OpenAI-compatible model used as the Chutes prover preset.
CHUTES_OPENAI_BASE_URL = "https://llm.chutes.ai/v1"
OFFICIAL_OPENAI_BASE_URL = "https://api.openai.com/v1"
CHUTES_DEFAULT_MODEL = CANONICAL_JUDGE_OPENAI_MODEL
# Matches LemmaSettings.anthropic_model default (prover falls back if PROVER_MODEL unset).
DEFAULT_ANTHROPIC_MODEL = "claude-3-5-sonnet-20241022"

# Google Gemini OpenAI-compatible API (miner prover only in the wizard).
GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
# (menu number, PROVER_MODEL id, one-line hint). Google may retarget `-latest` aliases over time.
_GEMINI_PRESET_ROWS: tuple[tuple[str, str, str], ...] = (
    ("1", "gemini-pro-latest", "Pro tier — strongest; highest typical $/token (tiered by context)."),
    ("2", "gemini-flash-latest", "Flash — strong default for miners; mid-range $/token."),
    ("3", "gemini-flash-lite-latest", "Flash-Lite — cheaper / faster when quality tradeoffs are OK."),
)

# Bittensor testnet RPC — docs/getting-started.md
CHAIN_ENDPOINT_TEST = "wss://test.finney.opentensor.ai:443"

# Lemma subnet on testnet
LEMMA_TESTNET_NETUID = 467

# Finney (mainnet) — not wired in ``collect_chain_updates`` yet. When Lemma registers on Finney, add a
# branch here (and a wizard/menu option if desired). Standard RPC is:
#   ``wss://entrypoint-finney.opentensor.ai:443``
# Set ``NETUID`` to the assigned subnet id (not sn0 — that is the root network).


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
    network, endpoint = "test", CHAIN_ENDPOINT_TEST
    netuid = LEMMA_TESTNET_NETUID
    click.echo(
        stylize("→ ", dim=True)
        + stylize(network, fg="cyan")
        + stylize(f"  NETUID {netuid}  ", dim=True)
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


_PROVER_BACKENDS_ORDERED: tuple[str, ...] = ("chutes", "gemini", "anthropic", "openai", "custom_openai")


def _resolve_backend_token(raw: str, ordered: tuple[str, ...]) -> str:
    """Accept ``1`` … ``n`` or an exact backend keyword from ``ordered`` (case-insensitive)."""
    s = raw.strip()
    if not s:
        return ordered[0]
    low = s.lower()
    if low.isdigit():
        n = int(low)
        if 1 <= n <= len(ordered):
            return ordered[n - 1]
        raise click.UsageError(
            f"Invalid number {n!r}. Type 1–{len(ordered)} or one of: {', '.join(ordered)}."
        )
    for b in ordered:
        if low == b.lower():
            return b
    raise click.UsageError(
        f"Unknown backend {raw!r}. Type 1–{len(ordered)} or one of: {', '.join(ordered)}."
    )


def _prompt_backend_menu(
    *,
    ordered: tuple[str, ...],
    default_slug: str,
    preamble: str,
    slug_hints: dict[str, str] | None = None,
) -> str:
    default_num = ordered.index(default_slug) + 1
    click.echo(preamble, nl=False)
    for i, name in enumerate(ordered, start=1):
        line = stylize(f"  {i}  ", fg="green", bold=True) + stylize(name, fg="cyan")
        if slug_hints and name in slug_hints:
            line += stylize(f" — {slug_hints[name]}", dim=True)
        click.echo(line + "\n", nl=False)
    click.echo(
        stylize(
            f"Reply with a row number (1–{len(ordered)}) or the left-column keyword; Enter alone keeps ",
            dim=True,
        )
        + stylize(f"{default_num} ({default_slug})", fg="cyan")
        + stylize(".\n", dim=True),
        nl=False,
    )
    raw = click.prompt(
        stylize("Backend", fg="green"),
        default=str(default_num),
        show_default=False,
    )
    return _resolve_backend_token(raw, ordered)


def _prover_backend_choice() -> str:
    preamble = (
        stylize("Mining prover — pick a vendor (writes Submission.lean); keys and models come next.\n", dim=True)
        + stylize("Rows 1–4 use preset URLs; row 5 asks for your own OpenAI-compat base URL.\n", dim=True)
    )
    return _prompt_backend_menu(
        ordered=_PROVER_BACKENDS_ORDERED,
        default_slug="chutes",
        preamble=preamble,
    )


def _prompt_gemini_prover_model() -> str:
    """Return PROVER_MODEL for Gemini OpenAI-compat (preset slug or custom id)."""
    click.echo(
        stylize(
            "Gemini `-latest` ids follow Google’s current default for that tier; pricing and the concrete model "
            "can change when Google updates the alias. Pin a versioned id in `.env` if you need stability.\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(
        stylize(
            "Cost (rough): Google charges per million input tokens and per million output tokens. "
            "After a few runs, check usage in Google AI Studio / Cloud billing. To estimate one call yourself: "
            "(prompt_tokens / 1e6) * price_in + (completion_tokens / 1e6) * price_out using the current table at ",
            dim=True,
        )
        + stylize("https://ai.google.dev/pricing", fg="yellow")
        + stylize(
            ". Lemma caps how large a completion can be with LEMMA_PROVER_MAX_TOKENS in `.env` (that is only an "
            "upper bound — real output is often smaller).\n",
            dim=True,
        ),
        nl=False,
    )
    click.echo(stylize("Pick a model (number):\n", dim=True), nl=False)
    for num, mid, blurb in _GEMINI_PRESET_ROWS:
        click.echo(
            stylize(f"  {num} ", fg="green", bold=True)
            + stylize(mid, fg="cyan")
            + stylize(f" — {blurb}\n", dim=True),
            nl=False,
        )
    click.echo(
        stylize("  4 ", fg="green", bold=True)
        + stylize("other Gemini id", fg="cyan")
        + stylize(" — you type the exact model string (same URL as above).\n", dim=True),
        nl=False,
    )
    choice = click.prompt(
        stylize("Model", fg="green"),
        type=click.Choice(["1", "2", "3", "4"], case_sensitive=False),
        default="2",
        show_default=True,
    ).strip()
    if choice == "4":
        mid = click.prompt(
            stylize("Gemini model id", fg="green") + stylize(" (e.g. gemini-2.0-flash)", dim=True),
            default="",
            show_default=False,
        ).strip()
        if not mid:
            raise click.UsageError("Gemini model id cannot be empty.")
        return mid
    for num, mid, _blurb in _GEMINI_PRESET_ROWS:
        if choice == num:
            return mid
    raise click.UsageError(f"Unexpected Gemini model choice: {choice!r}")


def collect_prover_updates() -> dict[str, str]:
    backend = _prover_backend_choice().lower()
    updates: dict[str, str]
    if backend == "chutes":
        click.echo(
            stylize(
                "Chutes: OpenAI-compatible API at llm.chutes.ai (URL is preset). Use your Chutes token. "
                f"PROVER_MODEL is the Chutes catalog id string, e.g. {CHUTES_DEFAULT_MODEL!r} on Enter, "
                "or deepseek-ai/DeepSeek-R1-0528-TEE — list ids from Chutes (curl …/v1/models).\n",
                dim=True,
            ),
            nl=False,
        )
        key = _require_secret("Chutes API key (prover)")
        click.echo(
            stylize(
                "PROVER_MODEL / PROVER_OPENAI_BASE_URL are miner-only; validator weights come from "
                "proofs that verify for the theorem.",
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
            "PROVER_OPENAI_API_KEY": key,
            "PROVER_OPENAI_BASE_URL": CHUTES_OPENAI_BASE_URL,
            "PROVER_MODEL": use_model,
        }
        click.echo(
            stylize("→ will write prover + key to .env; prover model ", dim=True)
            + stylize(use_model, fg="green")
            + stylize("\n", dim=True),
            nl=False,
        )
    elif backend == "gemini":
        click.echo(
            stylize(
                "Gemini: URL preset; Google AI Studio key next. PROVER_MODEL becomes e.g. gemini-flash-latest "
                "(menu presets) or a typed id such as gemini-3.1-pro-preview (see Google’s model names).\n",
                dim=True,
            ),
            nl=False,
        )
        key = _require_secret("Google AI Studio / Gemini API key (OpenAI-compatible)")
        model = _prompt_gemini_prover_model()
        updates = {
            "PROVER_PROVIDER": "openai",
            "PROVER_OPENAI_API_KEY": key,
            "PROVER_OPENAI_BASE_URL": GEMINI_OPENAI_BASE_URL,
            "PROVER_MODEL": model,
        }
        click.echo(
            stylize("→ will write PROVER_* for Gemini at ", dim=True)
            + stylize(GEMINI_OPENAI_BASE_URL, fg="yellow")
            + stylize("; model ", dim=True)
            + stylize(model, fg="green")
            + stylize(" (key not printed).\n", dim=True),
            nl=False,
        )
    elif backend == "anthropic":
        click.echo(
            stylize(
                "Anthropic: native Claude API (not OpenAI-compatible JSON). URL is preset. "
                f"Example PROVER_MODEL: {DEFAULT_ANTHROPIC_MODEL!r} (default on Enter) or claude-sonnet-4-20250514.\n",
                dim=True,
            ),
            nl=False,
        )
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
    elif backend == "openai":
        click.echo(
            stylize(
                "OpenAI: Chat Completions at api.openai.com (URL preset). Type PROVER_MODEL exactly as OpenAI names "
                "it, e.g. gpt-4o, gpt-5.1, o4-mini — no default.\n",
                dim=True,
            ),
            nl=False,
        )
        key = _require_secret("OpenAI API key (prover)")
        model = click.prompt(
            stylize("PROVER_MODEL", fg="green") + stylize(" (e.g. gpt-4o)", dim=True),
            default="",
            show_default=False,
        ).strip()
        if not model:
            raise click.UsageError("PROVER_MODEL is required for OpenAI.")
        updates = {
            "PROVER_PROVIDER": "openai",
            "PROVER_OPENAI_API_KEY": key,
            "PROVER_OPENAI_BASE_URL": OFFICIAL_OPENAI_BASE_URL,
            "PROVER_MODEL": model,
        }
        click.echo(
            stylize(
                f"→ will write PROVER_OPENAI_BASE_URL={OFFICIAL_OPENAI_BASE_URL!r}; model ",
                dim=True,
            )
            + stylize(model, fg="green")
            + stylize(" (key not printed).\n", dim=True),
            nl=False,
        )
    elif backend == "custom_openai":
        click.echo(
            stylize(
                "Custom: any host with OpenAI-compatible /v1/chat/completions. Base URL + key + PROVER_MODEL — "
                "the model string is whatever that host expects (Together, Groq, local vLLM, … all differ). "
                "Examples: base https://api.together.xyz/v1 with model meta-llama/Llama-3.3-70B-Instruct-Turbo; "
                "local http://127.0.0.1:8000/v1 with the id shown by your server’s /v1/models.\n",
                dim=True,
            ),
            nl=False,
        )
        key = _require_secret("OpenAI-compatible API key (prover)")
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
            "PROVER_OPENAI_API_KEY": key,
            "PROVER_OPENAI_BASE_URL": url,
            "PROVER_MODEL": model,
        }
    else:
        raise click.UsageError(f"Unexpected backend: {backend!r}")
    return updates


def collect_prover_retries_updates() -> dict[str, str]:
    """LEMMA_PROVER_LLM_RETRY_ATTEMPTS — transient LLM errors per forward / preview."""
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
    """Set only PROVER_MODEL for miner/prover runs."""
    click.echo(
        stylize(
            "This name is sent to your prover API as the model id (miner and `lemma preview`).",
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
        + stylize(" or any capable proof model on Chutes.\n", dim=True),
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
    """Expected-hash pins matching **current** `lemma meta`."""
    from lemma.judge.profile import judge_profile_sha256
    from lemma.problems.generated import generated_registry_sha256

    out: dict[str, str] = {"LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED": judge_profile_sha256(settings).strip().lower()}
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
        merge_prompted(env_path, "Validator — Lean Docker image", collect_lean_image_updates)
    else:
        merge_prompted(env_path, "Miner — prover LLM", collect_prover_updates)
        merge_prompted(env_path, "Miner — axon", collect_axon_updates)
        merge_prompted(env_path, "Validator — Lean Docker image", collect_lean_image_updates)

    click.echo("")
    click.echo(stylize("── Done ──", fg="green", bold=True))
    click.echo(
        stylize("  • Send TAO to your ", dim=True)
        + stylize("coldkey", fg="yellow")
        + stylize(" for registration fees (", dim=True)
        + stylize("hotkeys", fg="yellow")
        + stylize(" are not funded), then register on-chain with ", dim=True)
        + stylize("btcli", fg="yellow")
        + stylize(".\n", dim=True),
        nl=False,
    )
    if role in ("validator", "both"):
        click.echo(
            stylize("  • Validator: build image → ", dim=True)
            + stylize("bash scripts/prebuild_lean_image.sh", fg="yellow")
            + stylize("  then  ", dim=True)
            + stylize("lemma validator check", fg="green")
            + stylize("  before  ", dim=True)
            + stylize("lemma validator start", fg="green")
            + stylize(".\n", dim=True),
            nl=False,
        )
    if role in ("miner", "both"):
        click.echo(
            stylize("  • Miner: open ", dim=True)
            + stylize("AXON_PORT", fg="yellow")
            + stylize(" to the internet; check with ", dim=True)
            + stylize("lemma miner dry-run", fg="green")
            + stylize(".\n", dim=True),
            nl=False,
        )
