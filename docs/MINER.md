# Miner

Full walkthrough (uv, **`btcli`**, **`lemma setup`**, **`lemma-run`**): [GETTING_STARTED.md](GETTING_STARTED.md).

That guide avoids hand-editing **`.env`**: use **`lemma setup`** (role **miner** or **both**) or **`lemma configure chain`** + **`lemma configure prover`** + **`lemma configure axon`**.

**Recommended LLM backend:** Chutes (OpenAI-compatible) when prompted — others are optional.

---

## Run

From repo root (with **`lemma-run`** or an activated **`.venv`**):

```bash
./scripts/lemma-run lemma miner --dry-run
./scripts/lemma-run lemma miner
```

Daily forward cap: **`MINER_MAX_FORWARDS_PER_DAY`** or **`lemma miner --max-forwards-per-day`**.

---

## Generated mode

Templates span easy/medium/hard; validator answer deadline is **`DENDRITE_TIMEOUT_S`** ([GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md)).

---

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
```

---

## Output contract

**`proof_script`** must be complete **`Submission.lean`** for the challenge theorem name.

---

## Models

Chutes (primary), self-hosted vLLM, Anthropic: [MODELS.md](MODELS.md).
