# Miner

Walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md) — `btcli`, `lemma setup`, `lemma-run`. Prefer prompts over hand-editing `.env` (`lemma configure chain`, `configure prover`, `configure axon`).

Inference: Chutes when prompted works for most setups.

## Run

```bash
./scripts/lemma-run lemma miner --dry-run
./scripts/lemma-run lemma miner
```

Daily forward cap: `MINER_MAX_FORWARDS_PER_DAY` or `lemma miner --max-forwards-per-day`.

## Seeing replies, correctness, and Lean status

Validators decide whether your proof typechecks; the miner process does not receive scores back on the axon path.

- Set `LEMMA_MINER_LOG_FORWARDS=1` to log each forward: reasoning excerpt and `proof_script` excerpt at INFO; raw model output is logged at DEBUG (enable e.g. `LOG_LEVEL=DEBUG` to see it).
- Set `LEMMA_MINER_LOCAL_VERIFY=1` to run the same sandbox `lake build` as validators after the prover returns (requires Docker and `LEAN_SANDBOX_IMAGE` / timeouts aligned with your subnet). Logs `miner local verify OK` or `FAIL` with reason.

For frozen catalog problems, `LEMMA_MINER_LOCAL_VERIFY` needs the same `LEMMA_MINIF2F_CATALOG_PATH` as validators so `theorem_id` resolves.

## Generated mode

Templates span easy/medium/hard; answer deadline is `DENDRITE_TIMEOUT_S` ([GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md)).

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
```

## Output contract

`proof_script` must be complete `Submission.lean` for the challenge theorem name.

## Models

[MODELS.md](MODELS.md).
