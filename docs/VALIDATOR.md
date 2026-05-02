# Validator operations

## Prerequisites

1. **Wallet**: cold + hot registered on the target subnet (`btcli` — see [Bittensor docs](https://docs.learnbittensor.org/)).
2. **Lean sandbox image**: build once so `lake build` works offline inside Docker:

   ```bash
   bash scripts/prebuild_lean_image.sh
   ```

3. **Judge API**: Default stack is **`Qwen/Qwen3-32B-TEE`** at **`OPENAI_BASE_URL=https://llm.chutes.ai/v1`** ([Chutes](https://chutes.ai/)). Set **`OPENAI_API_KEY`** to your Chutes key. For local [vLLM](https://github.com/vllm-project/vllm), use `http://127.0.0.1:8000/v1` and the model id your server loads. Use **`LEMMA_FAKE_JUDGE=1`** to skip the LLM when testing. **Docker**: from inside the validator container, `127.0.0.1` is the container itself—if the judge runs on the host, point **`OPENAI_BASE_URL`** at the host (e.g. `http://host.docker.internal:8000/v1` on macOS/Windows, or the Docker bridge gateway on Linux). See [MODELS.md](MODELS.md).

## Configuration

Copy [.env.example](../.env.example) to `.env` and set:

- `NETUID`, `SUBTENSOR_NETWORK`, optional `SUBTENSOR_CHAIN_ENDPOINT`
- `BT_WALLET_COLD`, `BT_WALLET_HOT`
- `LEAN_SANDBOX_IMAGE` (default `lemma/lean-sandbox:latest`)
- `JUDGE_PROVIDER`, model env vars
- `DENDRITE_TIMEOUT_S`, `EMPTY_EPOCH_WEIGHTS_POLICY` (`skip` | `uniform`), `SET_WEIGHTS_*` retries
- Canonical rubric hash: `uv run lemma meta` (share across validators; see [GOVERNANCE.md](GOVERNANCE.md))

## Run

```bash
uv sync --extra dev
uv run lemma validator
```

Dry-run (no `set_weights`):

```bash
uv run lemma validator --dry-run
# or
LEMMA_DRY_RUN=1 uv run lemma validator
```

## Docker Compose

Requires Docker socket for Lean containers:

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

## Notes

- The validator waits until `blocks_until_next_epoch(netuid) <= 1` before each scoring round.
- Broader launch checklist: [PRODUCTION.md](PRODUCTION.md).
- Set `LEAN_SANDBOX_NETWORK=bridge` only if you must allow `lake` network during bootstrap; default is `none` with a pre-baked image.
