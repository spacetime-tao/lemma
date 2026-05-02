# Miner

Setup: [GETTING_STARTED.md](GETTING_STARTED.md).

## Requirements

- Registered hotkey on `NETUID`.
- Prover credentials (`PROVER_PROVIDER`, `ANTHROPIC_*` / `OPENAI_*` per `.env`).
- **`AXON_PORT`** reachable from validators; **`AXON_EXTERNAL_IP`** if public IP is not auto-detected (`AXON_DISCOVER_EXTERNAL_IP=false` to disable discovery).

## Generated mode

Templates span easy/medium/hard buckets; answer deadline is **`DENDRITE_TIMEOUT_S`** on validators ([GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md)).

## Configuration

See [`.env.example`](../.env.example): `NETUID`, `AXON_*`, `PROVER_*`, optional `MINER_*` gates and **`SYNAPSE_MAX_*`**.

## Commands

```bash
uv sync --extra dev
uv run lemma miner --dry-run
uv run lemma miner
```

Daily forward cap: **`MINER_MAX_FORWARDS_PER_DAY`** or **`lemma miner --max-forwards-per-day`** → HTTP **429** after limit (`~/.lemma/miner_daily_forwards.json`).

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
```

## Output

**`proof_script`** must be complete **`Submission.lean`** matching the challenge theorem name. Without API keys the stub proves only the bundled demo.

## Models

Chutes and other OpenAI-compatible endpoints: [MODELS.md](MODELS.md).
