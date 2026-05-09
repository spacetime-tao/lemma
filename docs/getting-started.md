# Getting started

End-to-end: **uv** + repo → **keys** → **`lemma-cli setup`** → **miner or validator**. Sections below are copy-paste commands (swap wallet names and paths if yours differ).

- Run `uv run lemma` for core command help (same as `uv run lemma --help`). The friendly operator screen lives in the separate [lemma-cli](https://github.com/spacetime-tao/lemma-cli) repo.
- Inference defaults: [Chutes](https://chutes.ai) OpenAI-compatible `https://llm.chutes.ai/v1` (see `.env.example`). Other OpenAI-compatible stacks use the same env vars.
- After setup: `uv run lemma status`, then `uv run lemma problems` (or `uv run lemma problems show --current`). Deep reference: [faq](faq.md).
- **On-chain try:** Lemma runs on **Bittensor testnet** (`--network test`), **netuid 467**. **Finney** is mainnet—do not confuse the two. The repo is still largely proof-of-concept; long-term direction is in [vision](vision.md).

## Paths at a glance

**Miner (most common first path):** `uv sync` → keys (`uv run btcli`) → `lemma-cli setup` → fund wallet → `uv run btcli subnet register --netuid 467 --network test …` → `uv run lemma miner dry-run` → **`lemma-cli rehearsal`** (optional: live theorem → prover → Lean → judge preview) → open `AXON_PORT` → `uv run lemma miner start`. Details: [miner.md](miner.md).

**Validator:** same env/keys/setup as above, then **`bash scripts/prebuild_lean_image.sh`** (first build is large) → **`lemma-cli rehearsal`** (recommended preview) → `uv run lemma validator-check` → `uv run lemma validator start`. Prefer explicit `uv run lemma validator start` / `uv run lemma validator dry-run` over ad-hoc Python entrypoints. Details: [validator.md](validator.md).

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

## Run Local Commands

```bash
uv run lemma --help
uv run btcli --help
```

Run these from the repo root. If you activate `.venv`, you can omit `uv run`.

## Keys (Bittensor CLI: `btcli`)

Names you will enter in `lemma-cli setup`. Keys live under `~/.bittensor/wallets/`. Commands below use the **`btcli`** executable from **`bittensor-cli`** (see above).

```bash
uv run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
uv run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
uv run btcli wallet balance --wallet.name my_wallet
```

Registration and stake: [Bittensor CLI](https://docs.learnbittensor.org/).

## Configure (`lemma-cli setup`)

**Chain:** the wizard only sets **Bittensor testnet** and writes **`NETUID=467`** (no separate netuid question). Then: wallet names, API keys, axon port, judge, and (for validators) Lean image. **Finney (mainnet) is TBD** for `lemma-cli configure chain` — hand-edit `.env` if Lemma later registers on mainnet; see comments in `.env.example`. Seeds from `.env.example` if `.env` is missing.

```bash
lemma-cli setup
```

Incremental: `lemma-cli configure chain`, `configure prover`, `configure judge`, `configure axon`, `configure lean-image`.

## Register on-chain

Use the same network/netuid with `uv run btcli` as in `.env`: **Lemma (Subnet 467)** on **testnet** (`SUBTENSOR_NETWORK=test`), not Finney (mainnet).

```bash
uv run btcli subnet show --netuid 467 --network test
uv run btcli subnet register --netuid 467 --network test --wallet.name my_wallet --wallet.hotkey miner
```

## Miner

```bash
uv run lemma miner dry-run
uv run lemma miner start
```

Open inbound `AXON_PORT`. If `AXON_EXTERNAL_IP` is unset, discovery runs when `AXON_DISCOVER_EXTERNAL_IP=true` (default).

## Validator

Build sandbox image (first build is large):

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator dry-run
uv run lemma validator start
```

Use **`uv run lemma validator start`** only from the repo root. A legacy burn-to-UID-0 demo lives under **`examples/`** for reference.

Parity: `uv run lemma meta` — [governance.md](governance.md).

## Problem source

- `LEMMA_PROBLEM_SOURCE=generated` (default): block height seeds templates.
- `frozen`: catalog JSON — requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (public eval set); see [catalog-sources.md](catalog-sources.md).

More tuning: `.env.example` and `lemma-cli configure` where possible.

## Checklist

| Step | Command / action |
| ---- | ---------------- |
| Deps | `uv sync --extra dev` |
| Keys | `uv run btcli` coldkey + hotkey |
| Env | `lemma-cli setup` |
| Chain | Fund + `uv run btcli subnet register` |
| Miner | `uv run lemma miner start` |
| Validator | `prebuild_lean_image.sh`, `uv run lemma validator start` |

[miner.md](miner.md), [validator.md](validator.md), [models.md](models.md), [testing.md](testing.md).
