# Getting started

End-to-end: **uv** + repo → **keys** → **`lemma setup`** → **miner or validator**. Sections below are copy-paste commands (swap `<repository-url>`, wallet names, and paths).

- Run `lemma` or `lemma start` for the interactive menu (`setup`, `doctor`, `docs`, `status`, dry-runs, `meta`).
- Inference defaults: [Chutes](https://chutes.ai) OpenAI-compatible `https://llm.chutes.ai/v1` (see `.env.example`). Other OpenAI-compatible stacks use the same env vars.
- After setup: `lemma status`, then `lemma problems` (or `lemma problems show --current`). Deep reference: [faq](faq.md).

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

Parity: `./scripts/lemma-run lemma meta` — [governance.md](governance.md).

## Problem source

- `LEMMA_PROBLEM_SOURCE=generated` (default): block height seeds templates.
- `frozen`: catalog JSON — [catalog-sources.md](catalog-sources.md).

More tuning: `.env.example` and `lemma configure` where possible.

## Checklist

| Step | Command / action |
| ---- | ---------------- |
| Deps | `uv sync --extra dev` |
| Keys | `btcli` coldkey + hotkey |
| Env | `lemma setup` |
| Chain | Fund + `btcli subnet register` |
| Miner | `lemma miner` (menu) or `lemma miner start` |
| Validator | `prebuild_lean_image.sh`, `lemma validator` / `lemma validator start` |

[miner.md](miner.md), [validator.md](validator.md), [models.md](models.md), [testing.md](testing.md).
