# Validator

Setup: [GETTING_STARTED.md](GETTING_STARTED.md).

## Requirements

1. Wallets registered on `NETUID` (`btcli`; [Bittensor docs](https://docs.learnbittensor.org/)).
2. Lean sandbox image:

   ```bash
   bash scripts/prebuild_lean_image.sh
   ```

3. Judge HTTP API (default Chutes `Qwen/Qwen3-32B-TEE`; **`OPENAI_API_KEY`**). vLLM: `OPENAI_BASE_URL=http://127.0.0.1:8000/v1`. **`LEMMA_FAKE_JUDGE=1`** disables real judging for tests. From Docker to host inference use **`host.docker.internal`** (macOS/Windows) or the Docker bridge IP on Linux ([MODELS.md](MODELS.md)).

## Configuration

Copy [`.env.example`](../.env.example) → `.env`: `NETUID`, `SUBTENSOR_*`, `BT_WALLET_*`, `LEAN_SANDBOX_IMAGE`, judge vars, `DENDRITE_TIMEOUT_S`, `EMPTY_EPOCH_WEIGHTS_POLICY`, `SET_WEIGHTS_*`. Publish **`uv run lemma meta`** hashes ([GOVERNANCE.md](GOVERNANCE.md)).

## Commands

```bash
uv sync --extra dev
uv run lemma validator --dry-run
uv run lemma validator
```

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

## Behavior

Waits until `blocks_until_next_epoch(netuid) <= 1` before rounds. **`LEAN_SANDBOX_NETWORK=bridge`** only if bootstrap needs outbound network; otherwise **`none`** with a warm image. Operations checklist: [PRODUCTION.md](PRODUCTION.md).
