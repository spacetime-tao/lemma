# Getting started

End-to-end: **uv** + repo → **keys** → **`uv run lemma-cli setup`** → **miner or validator**. Sections below are copy-paste commands (swap wallet names and paths if yours differ).

- Run `uv run lemma` for core command help (same as `uv run lemma --help`). The friendly operator screen lives in the separate [lemma-cli](https://github.com/spacetime-tao/lemma-cli) repo.
- Inference defaults: [Chutes](https://chutes.ai) OpenAI-compatible `https://llm.chutes.ai/v1` (see `.env.example`). Other OpenAI-compatible stacks use the same env vars.
- After setup: `uv run lemma-cli status`, then `uv run lemma-cli problems` (or `uv run lemma-cli problems show --current`). Deep reference: [faq](faq.md).
- **On-chain try:** Lemma runs on **Bittensor testnet** (`--network test`), **netuid 467**. **Finney** is mainnet—do not confuse the two. The repo is still largely proof-of-concept; long-term direction is in [vision](vision.md).

## Paths at a glance

**Miner (most common first path):** `uv sync --extra btcli --extra cli` → keys (`uv run btcli`) → `uv run lemma-cli setup` → fund wallet → `uv run btcli subnet register --netuid 467 --network test …` → `uv run lemma miner dry-run` → **`uv run lemma-cli rehearsal`** (optional: live theorem → prover → Lean preview) → open `AXON_PORT` → `uv run lemma miner start`. Details: [miner.md](miner.md).

**Validator:** same env/keys/setup as above, then **`bash scripts/prebuild_lean_image.sh`** (first build is large) → **`uv run lemma-cli rehearsal`** (recommended preview) → `uv run lemma validator-check` → `uv run lemma validator start`. Prefer explicit `uv run lemma validator start` / `uv run lemma validator dry-run` over ad-hoc Python entrypoints. Details: [validator.md](validator.md).

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone and sync

```bash
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli --extra cli
# For development/testing instead: uv sync --extra dev --extra btcli --extra cli
```

Use one Python environment and one installer: `uv`. The core `lemma` repo owns
the subnet dependencies; the `cli` extra installs `lemma-cli` into the same
`.venv` so setup, doctor, status, and preview commands see the same `.env`,
packages, and `lemma` command.

Default `uv sync` installs from **PyPI** and keeps only the **`bittensor`** SDK needed by Lemma itself. Add `--extra btcli` when you want repo-local wallet/register commands: it pulls in the official **[bittensor-cli](https://pypi.org/project/bittensor-cli/)** package through **`bittensor[cli]`**. Add `--extra cli` for the friendly operator CLI. **`btcli`** is only the **command name** those packages put on your `PATH`—there is no legitimate PyPI package you should install called `btcli`; typosquat packages have existed, so always use **`bittensor`**, **`bittensor-cli`**, or **`bittensor[cli]`** from PyPI.

## Run Local Commands

```bash
uv run lemma --help
uv run btcli --help
uv run lemma-cli --help
```

Run these from the core `lemma` repo root. `uv run btcli` requires
`uv sync --extra btcli`; `uv run lemma-cli` requires `uv sync --extra cli`.

## Keys (Bittensor CLI: `btcli`)

Names you will enter in `lemma-cli setup`. Keys live under `~/.bittensor/wallets/`. Commands below use the **`btcli`** executable from **`bittensor-cli`** (see above).

```bash
uv run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
uv run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
uv run btcli wallet balance --wallet.name my_wallet
```

Registration and stake: [Bittensor CLI](https://docs.learnbittensor.org/).

## Configure (`uv run lemma-cli setup`)

**Chain:** the wizard only sets **Bittensor testnet** and writes **`NETUID=467`** (no separate netuid question). Then: wallet names, prover API keys, axon port, and (for validators) Lean image. **Finney (mainnet) is TBD** for `uv run lemma-cli configure chain` — hand-edit `.env` if Lemma later registers on mainnet; see comments in `.env.example`. Seeds from `.env.example` if `.env` is missing.

```bash
uv run lemma-cli setup
```

Incremental: `uv run lemma-cli configure chain`, `configure prover`, `configure axon`, `configure lean-image`.

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

Open inbound `AXON_PORT`. Set `AXON_EXTERNAL_IP` explicitly for production miners, or opt into HTTPS public-IP discovery with `AXON_DISCOVER_EXTERNAL_IP=true`.

## Validator

Build sandbox image (first build is large):

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator dry-run
uv run lemma validator start
```

Use **`uv run lemma validator start`** only from the repo root.

Parity: `uv run lemma meta` — [governance.md](governance.md).

## Problem source

- `LEMMA_PROBLEM_SOURCE=generated` (default): block height seeds templates.
- `frozen`: catalog JSON — requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (public eval set); see [catalog-sources.md](catalog-sources.md).

More tuning: `.env.example` and `uv run lemma-cli configure` where possible.

## Checklist

| Step | Command / action |
| ---- | ---------------- |
| Deps | `uv sync --extra btcli --extra cli` (`--extra dev` too if developing) |
| Keys | `uv run btcli` coldkey + hotkey |
| Env | `uv run lemma-cli setup` |
| Chain | Fund + `uv run btcli subnet register` |
| Miner | `uv run lemma miner start` |
| Validator | `prebuild_lean_image.sh`, `uv run lemma validator start` |

[miner.md](miner.md), [validator.md](validator.md), [models.md](models.md), [testing.md](testing.md).
