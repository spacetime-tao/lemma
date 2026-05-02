# Getting started

Follow the sections in order. Each block is copy-pasteable.

---

## 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Windows: [uv installation](https://docs.astral.sh/uv/getting-started/installation/).

---

## 2. Clone and install Python deps

```bash
git clone <repository-url>
cd lemma
uv sync --extra dev
```

**What you get:** editable package **`lemma`** (CLI), **`bittensor`**, and **`btcli`** via **`bittensor[cli]`** in `pyproject.toml`. Nothing runs until **`uv sync`** creates **`.venv/`**.

Optional extras: **`catalog`**, **`wandb`** ([CATALOG_SOURCES.md](CATALOG_SOURCES.md)).

---

## 3. Run `lemma` without typing `uv run` every time

After **`uv sync`**, activate the project venv. Then **`lemma`** and **`btcli`** are on your **`PATH`** for that shell.

**Linux / macOS**

```bash
cd lemma
source .venv/bin/activate
lemma --help
btcli --help
```

**Windows (cmd)**

```cmd
cd lemma
.venv\Scripts\activate.bat
lemma --help
```

**Windows (PowerShell)**

```powershell
cd lemma
.\.venv\Scripts\Activate.ps1
lemma --help
```

From here on, examples use **`lemma`**; if you skip activation, prefix with **`uv run`** (e.g. **`uv run lemma miner`**).

---

## 4. Environment file

```bash
cd lemma
cp .env.example .env
```

Edit **`.env`** (gitignored). Never commit secrets.

---

## 5. Paste API keys (optional helpers)

Merge keys into **`.env`** without editing by hand:

**Validator — judge (OpenAI-compatible or Anthropic)**

```bash
cd lemma
source .venv/bin/activate
lemma configure judge
```

You choose **openai** or **anthropic**, then paste the key when prompted (hidden). For OpenAI-compatible stacks you can add **`OPENAI_BASE_URL`** in the same flow.

**Miner — prover LLM**

```bash
lemma configure prover
```

Same idea: provider + key → **`PROVER_PROVIDER`** and **`OPENAI_*`** or **`ANTHROPIC_*`**.

---

## 6. Chain and wallets

1. Create cold/hot wallets with **`btcli`** (keys under **`~/.bittensor/wallets/`**).
2. Fund and register on your target **`NETUID`** ([Bittensor docs](https://docs.learnbittensor.org/)).

In **`.env`** set **`SUBTENSOR_NETWORK`**, **`SUBTENSOR_CHAIN_ENDPOINT`** if needed, **`NETUID`**, **`BT_WALLET_COLD`**, **`BT_WALLET_HOT`**.

---

## 7. Miner: axon IP and port

Validators must reach your miner at **`AXON_EXTERNAL_IP:AXON_PORT`**.

- If **`AXON_EXTERNAL_IP`** is **unset** and **`AXON_DISCOVER_EXTERNAL_IP=true`** (default), Lemma discovers your public IPv4 over HTTPS when the miner starts—no extra setup for many home/datacenter setups.
- Override with **`AXON_EXTERNAL_IP`** if discovery is wrong (NAT, multihomed host).
- Local-only testing: e.g. **`AXON_EXTERNAL_IP=127.0.0.1`**.

**See what would be used (safe; does not open the axon):**

```bash
cd lemma
source .venv/bin/activate
lemma miner --dry-run
```

Open inbound **`AXON_PORT`** (default **8091**) on your firewall / cloud security group.

**Run the miner**

```bash
lemma miner --dry-run
lemma miner
```

---

## 8. Validator: Lean Docker image

Validators need the sandbox image for **`lake build`** verification.

```bash
cd lemma
bash scripts/prebuild_lean_image.sh
```

Set **`LEAN_SANDBOX_IMAGE`** in **`.env`** to match what you built (see script output).

**Run the validator**

```bash
lemma validator --dry-run
lemma validator
```

---

## 9. Problem source modes

- **`LEMMA_PROBLEM_SOURCE=generated`** (default): block height seeds templates; ids like **`gen/<block>`**.
- **`frozen`**: **`minif2f_frozen.json`** — see [CATALOG_SOURCES.md](CATALOG_SOURCES.md).

---

## 10. Economics and ops

Inference cost scales with challenges × tokens × provider price. Epoch cadence follows subnet tempo, not **`DENDRITE_TIMEOUT_S`** (HTTP answer deadline). Cap miner spend: **`MINER_MAX_FORWARDS_PER_DAY`** or **`lemma miner --max-forwards-per-day`**.

**Comparator:** default off; see [COMPARATOR.md](COMPARATOR.md).

**Governance / hashes:** **`lemma meta`** — [GOVERNANCE.md](GOVERNANCE.md).

---

## Checklist

| Step | Miner | Validator |
| ---- | ----- | --------- |
| **`uv sync`** | ✓ | ✓ |
| **`.env`** | Prover keys, axon | Judge keys, **`LEAN_SANDBOX_IMAGE`** |
| Wallets + **`NETUID`** | ✓ | ✓ |
| Docker | Optional | Required for production verify |
| **`lemma configure`** | `configure prover` | `configure judge` |

More detail: [MINER.md](MINER.md), [VALIDATOR.md](VALIDATOR.md), [TESTING.md](TESTING.md).
