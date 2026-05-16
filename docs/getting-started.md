# Getting started

End-to-end: **uv** + repo → **keys** → **`uv run lemma setup`** → **`uv run lemma miner start`** or **`uv run lemma validator start`**. Sections below are copy-paste commands (swap wallet names and paths if yours differ).

- Run `uv run lemma` for command help (same as `uv run lemma --help`).
- Inference defaults: [Chutes](https://chutes.ai) OpenAI-compatible `https://llm.chutes.ai/v1` (see `.env.example`). Other OpenAI-compatible stacks use the same env vars.
- After setup: `uv run lemma status`, then `uv run lemma miner check` or `uv run lemma validator check`.
- **On-chain try:** Lemma runs on **Bittensor testnet** (`--network test`), **netuid 467**—miners can earn **testnet alpha** per subnet rules. **Finney** is **mainnet**; **mainnet alpha** applies only if Lemma (or your target deployment) is registered there with emissions—never confuse network or netuid. The repo is still largely proof-of-concept; direction is in [vision](vision.md).

## Paths at a glance

**Miner (most common first path):** `uv sync --extra btcli` → keys (`uv run btcli`) → `uv run lemma setup` → fund wallet → `uv run btcli subnet register --netuid 467 --network test …` → open `AXON_PORT` → `uv run lemma miner check` → `uv run lemma miner start`. Details: [miner.md](miner.md).

**Validator:** same env/keys/setup as above, then **`bash scripts/prebuild_lean_image.sh`** (first build is large) → `uv run lemma validator check` → `uv run lemma validator start`. Use `uv run lemma validator dry-run` to rehearse without set_weights. Details: [validator.md](validator.md).

**Bounties:** `uv run lemma bounty list` → `uv run lemma bounty show BOUNTY_ID` → `uv run lemma bounty verify BOUNTY_ID --submission Submission.lean` → `uv run lemma bounty submit BOUNTY_ID --submission Submission.lean --payout <SS58>`. Bounties are submit-when-ready and do not require miner registration. Details: [bounties.md](bounties.md).

## Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Clone and sync

```bash
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
# For development/testing instead: uv sync --extra dev --extra btcli
```

Use one Python environment and one installer: `uv`. The core `lemma` repo owns
the subnet dependencies and the `lemma` command. Setup, miner, validator,
theorem, proof, bounty, and status commands all read the same `.env`.

Default `uv sync` installs from **PyPI** and keeps only the **`bittensor`** SDK needed by Lemma itself. Add `--extra btcli` when you want repo-local wallet/register commands: it pulls in the official **[bittensor-cli](https://pypi.org/project/bittensor-cli/)** package through **`bittensor[cli]`**. **`btcli`** is only the **command name** those packages put on your `PATH`—there is no legitimate PyPI package you should install called `btcli`; typosquat packages have existed, so always use **`bittensor`**, **`bittensor-cli`**, or **`bittensor[cli]`** from PyPI.

## Run Local Commands

```bash
uv run lemma --help
uv run btcli --help
```

Run these from the core `lemma` repo root. `uv run btcli` requires
`uv sync --extra btcli`; `uv run lemma` works after the normal sync.

## Keys (Bittensor CLI: `btcli`)

Names you will enter in `lemma setup`. Keys live under `~/.bittensor/wallets/`. Commands below use the **`btcli`** executable from **`bittensor-cli`** (see above).

```bash
uv run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
uv run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
uv run btcli wallet balance --wallet.name my_wallet
```

Registration and stake: [Bittensor CLI](https://docs.learnbittensor.org/).

## Configure (`uv run lemma setup`)

**Chain:** the wizard only sets **Bittensor testnet** and writes **`NETUID=467`** (no separate netuid question). Then: wallet names, prover API keys, axon port, and (for validators) Lean image. **Finney (mainnet) is TBD** for setup — hand-edit `.env` if Lemma later registers on mainnet; see comments in `.env.example`.

```bash
uv run lemma setup
```

Default setup is miner-first. Use `uv run lemma setup --role validator` or `uv run lemma setup --role both` for validator machines.

## Register on-chain

Use the same network/netuid with `uv run btcli` as in `.env`: **Lemma (Subnet 467)** on **testnet** (`SUBTENSOR_NETWORK=test`), not Finney (mainnet).

```bash
uv run btcli subnet show --netuid 467 --network test
uv run btcli subnet register --netuid 467 --network test --wallet.name my_wallet --wallet.hotkey miner
```

## Miner

```bash
uv run lemma miner check
uv run lemma miner start
```

Open inbound `AXON_PORT`. Set `AXON_EXTERNAL_IP` explicitly for production miners, or opt into HTTPS public-IP discovery with `AXON_DISCOVER_EXTERNAL_IP=true`.

Multiple hotkeys under one cold wallet can run from the same checkout by
overriding the hotkey and port at run time:

```bash
uv run lemma miner start --hotkey my_second_hotkey --port 8092
```

## Validator

Build sandbox image (first build is large):

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator dry-run
uv run lemma validator start
```

Use **`uv run lemma validator start`** only from the repo root.

## Problem source

- `LEMMA_PROBLEM_SOURCE=hybrid` (default): block height seeds a deterministic mix of generated templates and curated catalog rows.
- `generated`: generated templates only, useful for rollback/focused testing.
- `frozen`: catalog JSON — requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (public eval set); see [catalog-sources.md](catalog-sources.md).

More tuning: `.env.example` and the advanced hidden CLI commands where needed.

## Checklist

| Step | Command / action |
| ---- | ---------------- |
| Deps | `uv sync --extra btcli` (`--extra dev` too if developing) |
| Keys | `uv run btcli` coldkey + hotkey |
| Env | `uv run lemma setup` |
| Chain | Fund + `uv run btcli subnet register` |
| Miner | `uv run lemma miner start` |
| Validator | `prebuild_lean_image.sh`, `uv run lemma validator start` |

[miner.md](miner.md), [validator.md](validator.md), [bounties.md](bounties.md), [models.md](models.md), [testing.md](testing.md).
