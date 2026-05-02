# Miner

End-to-end flow: install → **`.env`** → wallets → axon reachable → run.

---

## 1. Install and shell

```bash
git clone <repository-url>
cd lemma
uv sync --extra dev
source .venv/bin/activate
```

(Windows: **`.venv\Scripts\activate`**.)

---

## 2. Base `.env`

```bash
cp .env.example .env
```

Set at least **`NETUID`**, **`SUBTENSOR_*`**, **`BT_WALLET_COLD`**, **`BT_WALLET_HOT`**, **`AXON_PORT`**.

---

## 3. Prover API keys (interactive)

```bash
cd lemma
source .venv/bin/activate
lemma configure prover
```

Choose **openai** or **anthropic**, paste the key when prompted. This merges **`PROVER_PROVIDER`** and **`OPENAI_*`** or **`ANTHROPIC_*`** into **`.env`**.

To set **`PROVER_MODEL`**, **`OPENAI_BASE_URL`**, or caps by hand, edit **`.env`** after (see [`.env.example`](../.env.example)).

---

## 4. Axon reachability (automatic + checks)

**Default behavior:** if **`AXON_EXTERNAL_IP`** is empty and **`AXON_DISCOVER_EXTERNAL_IP=true`**, the miner discovers your public IPv4 at startup (same logic as production).

**See resolved settings without starting the axon:**

```bash
lemma miner --dry-run
```

You should see **`axon_external_ip=...`** (from env, or a probe of what auto-discovery would use). If discovery fails, set **`AXON_EXTERNAL_IP`** to your public IPv4 and ensure **`AXON_PORT`** is open to validators.

---

## 5. Run

```bash
lemma miner --dry-run
lemma miner
```

Daily forward cap: **`MINER_MAX_FORWARDS_PER_DAY`** or **`lemma miner --max-forwards-per-day`** → HTTP **429** after limit; state under **`~/.lemma/miner_daily_forwards.json`**.

---

## Generated mode

Templates span easy/medium/hard; answer deadline on validators is **`DENDRITE_TIMEOUT_S`** ([GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md)).

---

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
```

---

## Output contract

**`proof_script`** must be complete **`Submission.lean`** for the challenge theorem name. Without API keys the stub only proves the bundled demo.

---

## Models

Chutes and other OpenAI-compatible endpoints: [MODELS.md](MODELS.md).
