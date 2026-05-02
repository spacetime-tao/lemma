# Getting started (plain-language guide)

This page is for someone who has never run Lemma before: what to install, in what order, and how miners differ from validators. It complements [MINER.md](MINER.md), [VALIDATOR.md](VALIDATOR.md), and [SYSTEM_REQUIREMENTS.md](SYSTEM_REQUIREMENTS.md).

## Names that confuse people

| Name | What it is |
| ---- | ---------- |
| **`lemma`** | The Lemma **CLI** for this repo. There is no separate `lemma-cli` package—the console script is declared in `pyproject.toml` as `lemma`. After setup you run `lemma --help`, `lemma miner`, `lemma validator`. |
| **`uv`** | Fast Python installer/env manager ([Astral uv](https://docs.astral.sh/uv/)). Use it instead of juggling `pip` + `venv` by hand. |
| **`btcli`** | Bittensor **wallet + chain** CLI. It is installed when **`uv sync`** resolves **`bittensor[cli]`** (PyPI); it is **not** a separate clone step. Invoke **`uv run btcli`** from this repo (or activate `.venv` first). |

## 1. Install uv

macOS/Linux (official installer):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Follow any post-install notes so `uv` is on your `PATH`. On Windows, see the [uv install docs](https://docs.astral.sh/uv/getting-started/installation/).

You do **not** download Bittensor or **`btcli`** by cloning alone—that happens when **`uv sync`** installs **`pyproject.toml`** dependencies into **`.venv`**.

You do **not** need a separate `pip` install of Lemma if you use **`uv sync`** inside the repo (next step). If you prefer classic tooling: create **`python -m venv .venv`**, activate it, then **`pip install -e ".[dev]"`** from the repo root—the **`lemma`** and **`btcli`** commands land in that venv the same way.

## 2. Get the Lemma code and Python env

```bash
git clone <this-repository-url>
cd lemma
uv sync --extra dev
```

**What each step does**

| Step | Result |
| ---- | ------ |
| **`git clone`** | Source tree only (no Python packages yet). |
| **`uv sync --extra dev`** | Creates **`.venv`**, installs **`lemma`** (editable), **`bittensor[cli]`** (library + **`btcli`**), and dev tools (**`pytest`**, **`ruff`**, …). |

Optional groups: **`catalog`** (large catalog builds — see [CATALOG_SOURCES.md](CATALOG_SOURCES.md)), **`wandb`**. Use **`uv sync --all-extras`** only if you need every optional extra.

**Secrets:** copy **[`.env.example`](../.env.example)** to **`.env`** and fill in keys. **`.env`** is gitignored — never **`git add -f .env`**; share only **`.env.example`** or subnet ops templates.

Optional: activate the virtualenv so you can type **`lemma`** instead of **`uv run lemma`**:

```bash
source .venv/bin/activate   # Linux/macOS
lemma --help
```

You should see Click commands: **`miner`**, **`validator`**, **`meta`**, **`verify`**, etc. Contributors: run **`uv run pytest`** / **`uv run ruff`** as in [TESTING.md](TESTING.md).

## 3. Bittensor wallet and subnet registration

Lemma runs on a **Bittensor subnet**. You need:

1. A **cold** wallet and **hot** wallet (names stored under `~/.bittensor/wallets/`).
2. Enough TAO (or test funds on a testnet) to register your hotkey on the target **`NETUID`**.

Use `btcli`—from this repo:

```bash
uv run btcli --help
```

Exact flows change over time; follow the current **[Bittensor docs](https://docs.learnbittensor.org/)** for creating wallets, funding, and `subnet register`. Copy [.env.example](../.env.example) to `.env` and set:

- `SUBTENSOR_NETWORK`, `SUBTENSOR_CHAIN_ENDPOINT` (if not default)
- `NETUID`
- `BT_WALLET_COLD`, `BT_WALLET_HOT`

## 4. Configure environment variables

Lemma reads **`.env`** in the project root (copy from **[`.env.example`](../.env.example)** if you have not already — see step 2).

**Everyone:**

- Chain + wallet variables above.
- `LOG_LEVEL` if you want quieter logs.

**Miners** (proving side):

- `AXON_PORT`, `AXON_EXTERNAL_IP` (must be reachable from validators).
- **Prover LLM** (generates Lean proofs): set **`PROVER_PROVIDER`** (`anthropic` or `openai`), API keys, and optionally **`PROVER_MODEL`**. Keys reuse `ANTHROPIC_*` / `OPENAI_*` unless you only run a miner—see below.

**Validators** (grading side):

- **`LEAN_SANDBOX_IMAGE`** after you build the Lean image (step 5).
- **Judge LLM** (scores reasoning traces): **`JUDGE_PROVIDER`**, **`OPENAI_BASE_URL`**, **`OPENAI_MODEL`**, **`JUDGE_TEMPERATURE`**, **`JUDGE_MAX_TOKENS`**. Default expectation is a **single pinned stack** for every validator on the subnet (run **`uv run lemma meta`** and share the hashes—see [GOVERNANCE.md](GOVERNANCE.md)).
- Optional: **`JUDGE_PROFILE_SHA256_EXPECTED`** so your validator refuses to start if you typo a model name.

### API keys—two different roles

| Role | Env vars | Purpose |
| ---- | -------- | ------- |
| **Miner “prover”** | `PROVER_PROVIDER`, `PROVER_MODEL`, plus `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | Writes **`Submission.lean`** (and trace). Open-ended model choice is intentional: anything that emits valid Lean can compete. |
| **Validator “judge”** | `JUDGE_PROVIDER`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, etc. | Scores **reasoning quality** after Lean passes. **Should be one agreed model/settings across validators** on a live subnet. |

For **Anthropic (miner prover)**:

- Set `PROVER_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, optionally `ANTHROPIC_MODEL` / `PROVER_MODEL`.

For **OpenAI or OpenAI-compatible (miner prover)**:

- Set `PROVER_PROVIDER=openai`, `OPENAI_API_KEY`, `OPENAI_BASE_URL` (use `https://api.openai.com/v1` for OpenAI-hosted models), `OPENAI_MODEL` / `PROVER_MODEL`.

For **validator judge on local vLLM**:

- Defaults use **[Chutes](https://chutes.ai/)** (`OPENAI_BASE_URL=https://llm.chutes.ai/v1`). For self-hosted vLLM, run vLLM (or similar) and set `OPENAI_BASE_URL=http://127.0.0.1:8000/v1` (or `host.docker.internal` from Docker—see [VALIDATOR.md](VALIDATOR.md)). Model recommendations: [MODELS.md](MODELS.md).

Testing without real LLMs:

- Validators: **`LEMMA_FAKE_JUDGE=1`** skips the judge (testing only).

## 5. Docker and Lean (validators; miners optional)

**Validators** should use Docker for **proof verification** in a sandbox (see [VALIDATOR.md](VALIDATOR.md)):

```bash
bash scripts/prebuild_lean_image.sh
```

**Miners** usually **do not** need Docker for consensus—they only return source code; validators run Lean. You might still use Docker **compose** files in this repo to run the miner process in a container if you prefer ops symmetry.

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
# or
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

## 6. Run

**Miner:**

```bash
uv run lemma miner --dry-run    # config smoke test
uv run lemma miner
```

**Validator:**

```bash
uv run lemma validator --dry-run
uv run lemma validator
```

Share **`uv run lemma meta`** output with other operators so everyone pins the same judge profile where required.

## Is “open miner model + strict validator judge” a good idea?

**Roughly yes**, with caveats:

- **Lean** is the objective gate: a proof either typechecks under the agreed axioms or it fails—no amount of fancy wording fixes a broken proof.
- The **LLM judge** only affects scoring of **reasoning traces**, so keeping **one** judge stack on validators makes subjective scores comparable.
- Letting miners pick **any** prover stack encourages hardware/API diversity and research; the subnet still compares outputs under one rubric after verification.

If you want miners constrained to one model too, that becomes **subnet policy + client enforcement**, not something this repo forces.

## How expensive is mining if I’m always proving?

You pay for **LLM usage**, not for “having the miner online” by itself. Rough mental model:

1. **How often am I invoked?** Validators run scoring on **subnet epoch** boundaries (chain scheduling), not necessarily every wall-clock 5 minutes. Each epoch samples **one** theorem and queries miners (`DENDRITE_TIMEOUT_S` is how long you have to **answer**—default 3600s / 60 minutes in shipped config).
2. **How big are my calls?** One proof attempt can range from a short tactic script to a huge `Submission.lean` + trace—token counts swing order-of-magnitude by problem difficulty and model verbosity.
3. **Hosted APIs:** Cost ≈ *(epochs per day you respond to)* × *(average input + output tokens)* × *(provider $/1M tokens)*. Example: if you averaged **~50k output tokens** per challenge at **~$10/M output tokens**, that is **~$0.50/challenge** before input costs—scale linearly with challenge rate.
4. **Self-hosted models:** Swap subscription pricing for **GPU hire + electricity** (cloud A100/H100 hourly rates, or amortized home hardware).

Because subnet tempo and competition vary, **nobody can quote your exact monthly bill** without your epoch rate, model choice, and average tokens. Start with `--dry-run`, watch logs for token usage if you add instrumentation, or test on a cheap model first.

## Large catalogs vs “endless” problems

**Default (`LEMMA_PROBLEM_SOURCE=generated`):** each epoch uses the chain block as an integer seed and expands it into **one** theorem from a **built-in template registry** ([`GeneratedProblemSource`](../lemma/problems/generated.py)). Everyone runs the same Python code, so miners and validators agree with **no giant JSON file**.

**Optional frozen mode (`LEMMA_PROBLEM_SOURCE=frozen`):** load rows from `minif2f_frozen.json`. You can rebuild a large catalog with [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py) (see [CATALOG_SOURCES.md](CATALOG_SOURCES.md)). Changing templates or the frozen file should be treated like any other **subnet consensus upgrade**.

## Comparator—should I turn it on?

See [COMPARATOR.md](COMPARATOR.md). Short version:

- **Default for most subnets: leave it off.** Lean verification + axiom policy already enforce proofs.
- **If your subnet adopts a comparator:** then **every validator must use the same** `LEMMA_COMPARATOR_CMD` (and enable/disable flag)—otherwise scores are not comparable.

---

## Quick checklist

| Step | Miner | Validator |
| ---- | ----- | --------- |
| `uv sync` | ✓ | ✓ |
| Wallet + `NETUID` | ✓ | ✓ |
| `.env` | Prover keys, axon port/IP | Judge stack, **`uv run lemma meta`**, Lean image |
| Docker | Optional | Strongly recommended |
| `lemma miner` / `lemma validator` | ✓ | ✓ |
