# Getting started

Install order: **uv** → **clone** → **`uv sync`** → **`.env`** → **wallets** → **run**.

## Dependencies from `uv sync`

`pyproject.toml` declares **`bittensor[cli]`** (Python SDK + **`btcli`**) and this repo as an editable package (console script **`lemma`**). Cloning does not install them; **`uv sync`** writes everything under **`.venv/`**.

| Artifact | Role |
| -------- | ---- |
| **`lemma`** | CLI for miner, validator, `meta`, `verify`, … (`pyproject.toml` `[project.scripts]`). |
| **`bittensor`** | Subtensor client library used by miner/validator code. |
| **`btcli`** | Wallet and subnet registration CLI (from `bittensor[cli]`). |

Run with **`uv run lemma`** / **`uv run btcli`** or activate **`.venv`**.

## 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows: [uv installation](https://docs.astral.sh/uv/getting-started/installation/).

## 2. Clone and sync

```bash
git clone <repository-url>
cd lemma
uv sync --extra dev
```

Optional extras: **`catalog`** (catalog builders — [CATALOG_SOURCES.md](CATALOG_SOURCES.md)), **`wandb`**.

## 3. Environment file

Copy **[`.env.example`](../.env.example)** to **`.env`**. The file is gitignored; do not commit secrets.

## 4. Chain and wallets

1. Create cold/hot wallets (`btcli`; keys under `~/.bittensor/wallets/`).
2. Fund and register on the target **`NETUID`** per [Bittensor docs](https://docs.learnbittensor.org/).

Set in **`.env`**: `SUBTENSOR_NETWORK`, `SUBTENSOR_CHAIN_ENDPOINT` (if needed), `NETUID`, `BT_WALLET_COLD`, `BT_WALLET_HOT`.

## 5. Operator-specific variables

**All roles:** `LOG_LEVEL`.

**Miner:** `AXON_PORT`, `AXON_EXTERNAL_IP` (reachable from validators); prover: `PROVER_PROVIDER`, `ANTHROPIC_*` / `OPENAI_*`, optional `PROVER_MODEL`.

**Validator:** build Lean image (step 6); `LEAN_SANDBOX_IMAGE`; judge: `JUDGE_PROVIDER`, `OPENAI_*` / Chutes or vLLM — align subnet-wide; optional `JUDGE_PROFILE_SHA256_EXPECTED`. Run **`uv run lemma meta`** and publish hashes ([GOVERNANCE.md](GOVERNANCE.md)).

**Testing without LLM APIs:** `LEMMA_FAKE_JUDGE=1` (validators).

## 6. Lean Docker image (validators)

```bash
bash scripts/prebuild_lean_image.sh
```

Miners do not require Docker for consensus; validators use the sandbox image for `lake build`.

Optional Compose: `docker compose -f docker-compose.yml -f docker-compose.local.yml up miner` or `... up validator`.

## 7. Run

```bash
uv run lemma miner --dry-run
uv run lemma miner

uv run lemma validator --dry-run
uv run lemma validator
```

## Problem source modes

- **`LEMMA_PROBLEM_SOURCE=generated`** (default): block seed → one theorem from [`generated.py`](../lemma/problems/generated.py); ids `gen/<block>`.
- **`frozen`**: `minif2f_frozen.json`; rebuild with [CATALOG_SOURCES.md](CATALOG_SOURCES.md).

## Economics (mining)

Inference cost scales with **challenges answered** × **tokens** × **provider price**. Epoch spacing follows **subnet tempo**, not `DENDRITE_TIMEOUT_S` (HTTP answer deadline; default 3600s in shipped config). Cap forwards: `MINER_MAX_FORWARDS_PER_DAY` or `lemma miner --max-forwards-per-day`.

## Comparator

Default off; Lean + axioms suffice for v1. If enabled, all validators must share the same comparator settings ([COMPARATOR.md](COMPARATOR.md)).

## Checklist

| Item | Miner | Validator |
| ---- | ----- | --------- |
| `uv sync` | ✓ | ✓ |
| Wallets + `NETUID` | ✓ | ✓ |
| `.env` | Prover, axon | Judge, `lemma meta`, Lean image |
| Docker | Optional | Required for production verify |

Tests: [TESTING.md](TESTING.md).
