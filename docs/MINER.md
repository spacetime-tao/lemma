# Miner operations

First-time install (clone, **`uv sync`**, **`btcli`** wallets, **`.env`**): [GETTING_STARTED.md](GETTING_STARTED.md).

## Prerequisites

- Registered hotkey on the subnet.
- **Prover API**: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (see `PROVER_PROVIDER` in `.env`).
- **Reachable axon:** Lemma **guesses your public IP** when **`AXON_EXTERNAL_IP`** is blank (`AXON_DISCOVER_EXTERNAL_IP=false` to turn that off). You must still **expose port `AXON_PORT`** (router forward or cloud firewall)—software can’t punch the hole for you.

## Problem difficulty (generated mode)

Default challenges come from **deterministic templates** (not the giant frozen bank). Roughly **one third** are “easy,” **half** “medium,” **one fifth** “hard” per draw; the **answer deadline** is **`DENDRITE_TIMEOUT_S`** on validators (shipped default **60 minutes**), not baked into the theorem text—see [GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md) for the split and success-rate implications.

## Configuration

See [.env.example](../.env.example):

- `NETUID`, `AXON_PORT`, optional `AXON_EXTERNAL_IP` / `AXON_DISCOVER_EXTERNAL_IP`
- `PROVER_PROVIDER`, `PROVER_MODEL` (optional override)
- Optional prod gates: `MINER_MIN_VALIDATOR_STAKE`, `MINER_PRIORITY_BY_STAKE`, `MINER_MAX_CONCURRENT_FORWARDS`, synapse size caps (`SYNAPSE_MAX_*`)

## Run

```bash
uv sync --extra dev
uv run lemma miner
```

**Budget / spend control:** set **`MINER_MAX_FORWARDS_PER_DAY`** (or **`lemma miner --max-forwards-per-day N`**) to stop invoking the prover after **N** forwards each **UTC** day (persists in `~/.lemma/miner_daily_forwards.json`). Later validator queries get HTTP **429** until the next UTC day — you earn less but burn fewer tokens.

Config smoke test:

```bash
uv run lemma miner --dry-run
```

## Docker

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
```

## Output format

The miner must return **complete** `Submission.lean` source in `proof_script`, matching the theorem name in the challenge. Without API keys, the built-in stub only proves the bundled `two_plus_two` demo.

## Model ideas

- **[Chutes](https://chutes.ai/)** (recommended for cost and uniformity): set `PROVER_PROVIDER=openai`, `OPENAI_BASE_URL=https://llm.chutes.ai/v1`, pick an `OPENAI_MODEL` id from `GET https://llm.chutes.ai/v1/models`. Tradeoffs: [MODELS.md](MODELS.md).
- Other hosted APIs (Claude, OpenAI).
- Open weights such as [DeepSeek-Prover-V2](https://github.com/deepseek-ai/DeepSeek-Prover-V2) behind a local server (custom `Prover` adapter).
