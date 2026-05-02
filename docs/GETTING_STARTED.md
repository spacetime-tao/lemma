# Getting started

Goal: install deps, create keys with **`btcli`**, paste LLM API keys at prompts, run Lemma — **without hand-editing `.env`**.

Recommended inference for miners and validators: **[Chutes](https://chutes.ai)** OpenAI-compatible API at **`https://llm.chutes.ai/v1`** (subnet default model in `.env.example`). Anthropic and self-hosted OpenAI-compatible stacks are supported as secondary options via the same prompts.

---

## 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows: [uv installation](https://docs.astral.sh/uv/getting-started/installation/).

---

## 2. Clone and install Python packages

```bash
git clone <repository-url>
cd lemma
uv sync --extra dev
```

This creates **`.venv/`** and installs **`lemma`** (CLI), **`bittensor`**, and **`btcli`** (`bittensor[cli]`).

---

## 3. Save a one-line command: `lemma-run`

Use **`scripts/lemma-run`** so you never type **`uv run`** or **`source .venv`** for every command. It **`cd`**s to the repo, activates **`.venv`**, then runs whatever you pass:

```bash
cd lemma
chmod +x scripts/lemma-run
./scripts/lemma-run lemma --help
./scripts/lemma-run lemma miner --dry-run
```

**Optional — reuse from anywhere:** pick an absolute path once and add an alias (replace the path):

```bash
echo 'alias lemma-run='"'"'/ABS/PATH/TO/lemma/scripts/lemma-run'"'"'' >> ~/.zshrc
source ~/.zshrc
lemma-run lemma --help
```

Linux/bash users can append to **`~/.bashrc`** instead.

---

## 4. Create coldkey and hotkey (`btcli`)

These wallet names are what you will type into **`lemma setup`** in the next section. Keys live under **`~/.bittensor/wallets/`**.

**Create a cold wallet** (replace **`my_wallet`** with your name):

```bash
./scripts/lemma-run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
```

**Create a hotkey** on that cold wallet (replace **`miner`** with your hotkey name):

```bash
./scripts/lemma-run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
```

**Check balance** (after funding):

```bash
./scripts/lemma-run btcli wallet balance --wallet.name my_wallet
```

More commands (subnet registration, stake): [Bittensor CLI docs](https://docs.learnbittensor.org/) and your subnet operator docs.

---

## 5. Configure Lemma (no file editing)

**`lemma setup`** asks for **`NETUID`**, chain endpoint, **cold/hot wallet names**, API keys, axon port (miners), judge + Lean image settings (validators). Everything is merged into **`.env`** in the repo root. If **`.env`** does not exist yet, it is seeded from **`.env.example`** automatically.

```bash
cd lemma
./scripts/lemma-run lemma setup
```

Choose **miner**, **validator**, or **both**. Pick **Chutes** when asked for the inference backend unless you use Anthropic or a custom OpenAI-compatible endpoint — only your API key is required for Chutes.

**Incremental changes later** (same idea — prompts only):

```bash
./scripts/lemma-run lemma configure chain
./scripts/lemma-run lemma configure prover
./scripts/lemma-run lemma configure judge
./scripts/lemma-run lemma configure axon
./scripts/lemma-run lemma configure lean-image
```

---

## 6. Fund and register on-chain

Use **`btcli`** with your **`NETUID`** and the same **`--wallet.name`** / **`--wallet.hotkey`** you configured. Exact flow depends on subnet rules (burn vs PoW registration). Examples:

```bash
./scripts/lemma-run btcli subnet show --netuid <NETUID> --network finney
./scripts/lemma-run btcli subnet register --netuid <NETUID> --wallet.name my_wallet --wallet.hotkey miner
```

Use **`--network`** / endpoints consistent with **`lemma configure chain`** (default **finney**).

---

## 7. Miner: check axon, then run

```bash
./scripts/lemma-run lemma miner --dry-run
./scripts/lemma-run lemma miner
```

Open inbound **`AXON_PORT`** on your firewall. If **`AXON_EXTERNAL_IP`** is unset, Lemma discovers your public IPv4 at startup when **`AXON_DISCOVER_EXTERNAL_IP=true`** (default).

---

## 8. Validator: Lean Docker image, then run

Build the sandbox image (large download on first build):

```bash
cd lemma
bash scripts/prebuild_lean_image.sh
```

If **`lemma setup`** already set **`LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest`**, that matches the script’s extra tag.

```bash
./scripts/lemma-run lemma validator --dry-run
./scripts/lemma-run lemma validator
```

Fingerprints for subnet parity: **`./scripts/lemma-run lemma meta`** — [GOVERNANCE.md](GOVERNANCE.md).

---

## 9. Problem source modes

- **`LEMMA_PROBLEM_SOURCE=generated`** (default): block height seeds templates.
- **`frozen`**: catalog JSON — [CATALOG_SOURCES.md](CATALOG_SOURCES.md).

Advanced tuning still lives in **`.env.example`** for operators who need it; prefer **`lemma configure`** subcommands when possible.

---

## Checklist

| Step | Action |
| ---- | ------ |
| Install | **`uv sync --extra dev`** |
| Keys | **`btcli wallet new_coldkey`**, **`new_hotkey`** |
| Env | **`lemma setup`** (no manual `.env` edits) |
| Chain | Fund + **`btcli subnet register`** (or subnet-specific steps) |
| Miner | **`lemma miner`** |
| Validator | **`prebuild_lean_image.sh`**, **`lemma validator`** |

More detail: [MINER.md](MINER.md), [VALIDATOR.md](VALIDATOR.md), [MODELS.md](MODELS.md), [TESTING.md](TESTING.md).
