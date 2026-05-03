# Miner

Walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md) — `btcli`, `lemma setup`, `lemma-run`. Prefer prompts over hand-editing `.env` (`lemma configure chain`, `configure prover`, `configure axon`).

Inference: Chutes when prompted works for most setups.

## Run

```bash
./scripts/lemma-run lemma miner --dry-run
./scripts/lemma-run lemma miner
```

While the axon is up, each validator forward **starts the prover immediately** — there is no intentional delay for “new theorem” windows; you compete as soon as traffic hits your axon. By contrast, `lemma try-prover` is a manual one-off (same API billing pattern, but you pressed Enter).

Daily forward cap: `MINER_MAX_FORWARDS_PER_DAY` or `lemma miner start --max-forwards-per-day N`.

## Seeing replies, correctness, and Lean status

Validators decide whether your proof typechecks; the miner process does not receive scores back on the axon path.

- `lemma try-prover` runs the **prover once** on whatever theorem `lemma status` would sample right now, then prints informal reasoning and `proof_script` (uses your prover API). Add `--verify` to run Lean sandbox locally after (Docker).

- Set `LEMMA_MINER_LOG_FORWARDS=1` to log each forward: reasoning excerpt and `proof_script` excerpt at INFO; raw model output is logged at DEBUG (enable e.g. `LOG_LEVEL=DEBUG` to see it).
- Set `LEMMA_MINER_LOCAL_VERIFY=1` to run the same sandbox `lake build` as validators after the prover returns (requires Docker and `LEAN_SANDBOX_IMAGE` / timeouts aligned with your subnet). Logs `miner local verify OK` or `FAIL` with reason.

For frozen catalog problems, `LEMMA_MINER_LOCAL_VERIFY` needs the same `LEMMA_MINIF2F_CATALOG_PATH` as validators so `theorem_id` resolves.

## Generated mode

Templates span easy/medium/hard; how long validators wait on the wire follows **block height** (blocks to the next seed edge × `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, clamped) — see [GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md).

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
```

## Output contract

`proof_script` must be complete `Submission.lean` for the challenge theorem name.

## Models

Subnet validators score with a fixed judge model; miners should use a **reasoning**-oriented prover (documented in [MODELS.md](MODELS.md) — e.g. `deepseek-ai/DeepSeek-V3.2-TEE` on Chutes or another strong reasoning model you run well).
