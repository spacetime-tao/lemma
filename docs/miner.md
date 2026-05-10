# Miner

## Reference miner boundary

The bundled miner is a **reference Axon service** for the current Lemma subnet
protocol. It keeps the repo runnable end to end, gives operators a standard
prover path, and supports compatibility features such as local Lean verify,
miner attest, and commit-reveal.

It is not the long-term answer to the audit's "validator-only development" or
"container execution" ideals. Do not grow this package with competitive solver
strategy, broad onboarding UX, model experimentation dashboards, or alternate
transport stacks. Friendly flows belong in `lemma-cli`; major miner-artifact or
container-execution designs should be planned as separate protocol work.

Walkthrough: [getting-started.md](getting-started.md) — **`uv sync --extra btcli`** if you need repo-local **`uv run btcli`** (Bittensor CLI), `lemma-cli setup`, then `uv run lemma …` from the repo root. Prefer prompts over hand-editing `.env` (`lemma-cli configure chain`, `configure prover`, `configure axon`).

**Short checklist:** `lemma-cli setup` → coldkey funded → `uv run btcli subnet register` on the same network/netuid as `.env` → `uv run lemma miner dry-run` → **`lemma-cli rehearsal`** (see prover + Lean on the live theorem) → fix axon IP/port if needed → `uv run lemma miner start`. Run `uv run lemma` for core command help; run `lemma-cli` for the friendly operator screen.

### Prover LLM (`lemma-cli configure prover`)

Choose **which API** runs first (numbered menu), then follow prompts. **Chutes**, **Gemini** (preset tiers + custom id), **Anthropic**, **OpenAI**, or **custom** OpenAI-compatible URL — URLs are preset for all but **custom**. In-terminal blurbs show example **`PROVER_MODEL`** strings (catalog ids on Chutes, Gemini names, Claude ids, OpenAI model names; custom depends on the upstream host). Details and env vars: [models.md](models.md).

Inference: Chutes is the usual default when prompted.

## Run

```bash
uv run lemma miner dry-run
uv run lemma miner start
```

While the axon is up, each validator forward **starts the prover immediately** — there is no intentional delay for “new theorem” windows; you compete as soon as traffic hits your axon. By contrast, `lemma-cli try-prover` is a manual one-off (same API billing pattern, but you pressed Enter).

Daily forward cap: `MINER_MAX_FORWARDS_PER_DAY` or `uv run lemma miner start --max-forwards-per-day N`.

## Seeing replies, correctness, and Lean status

Validators decide whether your proof typechecks; the miner process does not receive scores back on the axon path.

- `lemma-cli try-prover` runs the **prover once** on whatever theorem `lemma-cli status` would sample right now, then prints `proof_script` (uses your prover API). Add `--verify` to run the Lean check after (default: Docker, same as validators).

- When a validator forward starts, logs include **`my_uid`** and **`my_incentive`** from the **chain metagraph** (same kind of aggregate view as `uv run btcli subnet show --netuid 467 --network test`) — a snapshot of subnet incentive for your hotkey, not a grade on this theorem.
- At **INFO** you get **`miner answered`** when the reply is ready; **`local_lean=`** is `PASS` / `FAIL` / … only if **`LEMMA_MINER_LOCAL_VERIFY=1`**. That flag is **optional**: validators always run Lean on your submission — enable local verify only if you want early PASS/FAIL on your machine (costs Docker CPU per forward while debugging). **`miner_forward_summary`** (default on) adds session rollups.

- Set `LEMMA_MINER_FORWARD_TIMELINE=1` for **three INFO lines per forward**: **`miner timeline 1 RECEIVE`** (theorem, `deadline_block` vs current head, HTTP/wall time budgets, short statement preview), **`miner timeline 2 SOLVED`** (prover wall time, sizes), **`miner timeline 3 OUTCOME`** (`local_lean` if `LEMMA_MINER_LOCAL_VERIFY=1`, else a hint). Then **`miner answered`** as today. Final validator weights are not returned on the axon — only optional **local Lean** mirrors validator proof-checking on your machine.

- Set `LEMMA_MINER_LOG_FORWARDS=1` to log each forward: `proof_script` excerpt at INFO; raw model output is logged at DEBUG (enable e.g. `LOG_LEVEL=DEBUG` to see it).
- Set `LEMMA_MINER_LOCAL_VERIFY=1` to run the same sandbox `lake build` as validators after the prover returns (requires Docker and `LEAN_SANDBOX_IMAGE` / timeouts aligned with your subnet). Logs `miner local verify OK` or `FAIL` with reason.

For frozen catalog problems, `LEMMA_MINER_LOCAL_VERIFY` needs the same `LEMMA_MINIF2F_CATALOG_PATH` as validators so `theorem_id` resolves.

## Generated mode

Templates span easy/medium/hard; how long validators wait on the wire follows **block height** (blocks to the next seed edge × `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, clamped) — see [generated-problems.md](generated-problems.md).

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up miner
```

## Output contract

`proof_script` must be complete `Submission.lean` for the challenge theorem name.

## Models

Miners should use a prover model that writes valid Lean reliably (documented in [models.md](models.md) — e.g. `deepseek-ai/DeepSeek-V3.2-TEE` on Chutes or another strong reasoning model you run well).
