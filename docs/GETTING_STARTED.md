# Getting started

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/), clone this repo, run `uv sync --extra dev`.
2. Run `lemma` or `lemma start` — interactive menu (`lemma setup`, `lemma doctor`, `lemma docs`, `lemma status`, dry-runs, `lemma meta`).
3. Create cold/hot keys with `btcli`, then `lemma setup` to merge settings into `.env` (no hand-editing required).

Inference for miners/validators: [Chutes](https://chutes.ai) OpenAI-compatible API at `https://llm.chutes.ai/v1` (default model in `.env.example`). Other OpenAI-compatible stacks work via the same env vars.

See what validators would sample: `lemma status`, then `lemma problems show --current`. More: [FAQ.md](FAQ.md).

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone and sync

```bash
git clone <repository-url>
cd lemma
uv sync --extra dev
```

Creates `.venv/` and installs `lemma`, `bittensor`, `btcli`.

## Optional: `lemma-run` wrapper

```bash
chmod +x scripts/lemma-run
./scripts/lemma-run lemma --help
```

From anywhere (replace path):

```bash
echo 'alias lemma-run='"'"'/ABS/PATH/TO/lemma/scripts/lemma-run'"'"'' >> ~/.zshrc
```

## Keys (`btcli`)

Names you will enter in `lemma setup`. Keys live under `~/.bittensor/wallets/`.

```bash
./scripts/lemma-run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
./scripts/lemma-run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
./scripts/lemma-run btcli wallet balance --wallet.name my_wallet
```

Registration and stake: [Bittensor CLI](https://docs.learnbittensor.org/).

## Configure (`lemma setup`)

Prompts for `NETUID`, chain, wallet names, API keys, axon port, judge and Lean image settings. Seeds from `.env.example` if `.env` is missing.

```bash
./scripts/lemma-run lemma setup
```

Incremental: `lemma configure chain`, `configure prover`, `configure judge`, `configure axon`, `configure lean-image`.

## Register on-chain

Match `--network` / endpoints to `lemma configure chain` (default finney).

```bash
./scripts/lemma-run btcli subnet show --netuid <NETUID> --network finney
./scripts/lemma-run btcli subnet register --netuid <NETUID> --wallet.name my_wallet --wallet.hotkey miner
```

## Miner

```bash
./scripts/lemma-run lemma miner --dry-run
./scripts/lemma-run lemma miner
```

Open inbound `AXON_PORT`. If `AXON_EXTERNAL_IP` is unset, discovery runs when `AXON_DISCOVER_EXTERNAL_IP=true` (default).

## Validator

Build sandbox image (first build is large):

```bash
bash scripts/prebuild_lean_image.sh
./scripts/lemma-run lemma validator --dry-run
./scripts/lemma-run lemma validator
```

Parity: `./scripts/lemma-run lemma meta` — [GOVERNANCE.md](GOVERNANCE.md).

## Problem source

- `LEMMA_PROBLEM_SOURCE=generated` (default): block height seeds templates.
- `frozen`: catalog JSON — [CATALOG_SOURCES.md](CATALOG_SOURCES.md).

More tuning: `.env.example` and `lemma configure` where possible.

## Checklist

| Step | Command / action |
| ---- | ---------------- |
| Deps | `uv sync --extra dev` |
| Keys | `btcli` coldkey + hotkey |
| Env | `lemma setup` |
| Chain | Fund + `btcli subnet register` |
| Miner | `lemma miner` |
| Validator | `prebuild_lean_image.sh`, `lemma validator` |

[MINER.md](MINER.md), [VALIDATOR.md](VALIDATOR.md), [MODELS.md](MODELS.md), [TESTING.md](TESTING.md).
