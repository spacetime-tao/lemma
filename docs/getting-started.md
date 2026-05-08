# Getting started

End-to-end: **uv** + repo → **keys** → **`lemma setup`** → **miner or validator**. Sections below are copy-paste commands (swap wallet names and paths if yours differ).

- Run `lemma start` for the interactive guided menu (`setup`, `doctor`, `docs`, `status`, dry-runs, `meta`). Run `lemma` alone for command help (same as `lemma --help`).
- Inference defaults: [Chutes](https://chutes.ai) OpenAI-compatible `https://llm.chutes.ai/v1` (see `.env.example`). Other OpenAI-compatible stacks use the same env vars.
- After setup: `lemma status`, then `lemma problems` (or `lemma problems show --current`). Deep reference: [faq](faq.md).
- **On-chain try:** Lemma runs on **Bittensor testnet** (`--network test`), **netuid 467**. **Finney** is mainnet—do not confuse the two. The repo is still largely proof-of-concept; long-term direction is in [vision](vision.md).

## Paths at a glance

**Miner (most common first path):** `uv sync` → keys (`btcli`) → `lemma setup` → fund wallet → `btcli subnet register --netuid 467 --network test …` → `lemma miner dry-run` (or **miner-dry** from `lemma start`) → **`lemma rehearsal`** (optional: live theorem → prover → Lean → judge preview) → open `AXON_PORT` → `lemma miner start`. Details: [miner.md](miner.md).

**Validator:** same env/keys/setup as above, then **`bash scripts/prebuild_lean_image.sh`** (first build is large) → **`lemma rehearsal`** (recommended preview) → `lemma validator-check` → `lemma validator start`. Prefer `lemma validator` / `lemma validator dry-run` over ad-hoc Python entrypoints. Details: [validator.md](validator.md).

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone and sync

```bash
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra dev
```

`uv sync` installs from **PyPI**: this repo depends on **`bittensor`** (SDK) and on **`bittensor[cli]`**, which pulls in the official **[bittensor-cli](https://pypi.org/project/bittensor-cli/)** package. **`btcli`** is only the **command name** those packages put on your `PATH`—there is no legitimate PyPI package you should install called `btcli`; typosquat packages have existed, so always use **`bittensor`**, **`bittensor-cli`**, or **`bittensor[cli]`** from PyPI.

## Optional: `lemma-run` wrapper

```bash
chmod +x scripts/lemma-run
./scripts/lemma-run lemma --help
```

From anywhere (replace path):

```bash
echo 'alias lemma-run='"'"'/ABS/PATH/TO/lemma/scripts/lemma-run'"'"'' >> ~/.zshrc
```

## Keys (Bittensor CLI: `btcli`)

Names you will enter in `lemma setup`. Keys live under `~/.bittensor/wallets/`. Commands below use the **`btcli`** executable from **`bittensor-cli`** (see above).

```bash
./scripts/lemma-run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
./scripts/lemma-run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
./scripts/lemma-run btcli wallet balance --wallet.name my_wallet
```

Registration and stake: [Bittensor CLI](https://docs.learnbittensor.org/).

## Configure (`lemma setup`)

Prompts for chain (Bittensor **testnet** only: `NETUID=467`); wallet names, API keys, axon port, judge and Lean image settings. **Finney (mainnet) is TBD** in the wizard — do not use fake `NETUID` values (e.g. sn0 is the root on Finney). Seeds from `.env.example` if `.env` is missing.

```bash
./scripts/lemma-run lemma setup
```

Incremental: `lemma configure chain`, `configure prover`, `configure judge`, `configure axon`, `configure lean-image`.

## Register on-chain

Point `lemma configure chain` at the same network you use with `btcli`. **Lemma (Subnet 467)** is on **testnet** (`test`), not Finney (Finney is **mainnet**).

```bash
./scripts/lemma-run btcli subnet show --netuid 467 --network test
./scripts/lemma-run btcli subnet register --netuid 467 --network test --wallet.name my_wallet --wallet.hotkey miner
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

Use **`lemma validator`** only — not `python validator.py` at the repo root (that file is a stub; a legacy burn-to-UID-0 demo lives under **`examples/`** for reference).

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
