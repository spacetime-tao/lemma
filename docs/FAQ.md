# FAQ

## Scoring

1. **Lean** must typecheck (kernel gate).
2. Among passing proofs, the **LLM judge** scores the reasoning trace (coherence, exploration, clarity).
3. **Pareto weighting** favors better scores and shorter traces ([`pareto.py`](../lemma/scoring/pareto.py)).

## Validator pipeline (each round)

1. Query miners (`proof_script` + reasoning).
2. **Docker sandbox:** `lake build`, axiom policy, optional comparator (local compute; not inference hosting).
3. If Lean passes: **judge** HTTP call (`JUDGE_PROVIDER`, `OPENAI_*`). May target Chutes, OpenAI, or vLLM depending on `OPENAI_BASE_URL`.

Miners call a separate **prover** API to generate proofs.

## Problem modes

| Mode | Behavior |
| ---- | -------- |
| `LEMMA_PROBLEM_SOURCE=generated` | Block seed → one of 22 templates ([`generated.py`](../lemma/problems/generated.py)). Unbounded ids (`gen/<block>`). |
| `frozen` | Rows from `minif2f_frozen.json`; finite pool. |

Template or catalog changes require coordinated upgrades ([GOVERNANCE.md](GOVERNANCE.md)).

## Timeouts

| Variable | Meaning |
| -------- | ------- |
| `DENDRITE_TIMEOUT_S` | HTTP wait for one miner response per challenge (default **300** s ≈ 5 min). |
| `LEAN_VERIFY_TIMEOUT_S` | Sandbox `lake build` budget after receipt (default **300** s). |
| `LEMMA_VALIDATOR_ROUND_INTERVAL_S` | Seconds between validator rounds when not aligning to epochs (default **300**). |
| `LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH` | `1` = wait for chain epoch before each round; default **`0`** (timer-based rounds). |

Round **frequency** defaults to **`LEMMA_VALIDATOR_ROUND_INTERVAL_S`** (wall-clock). Use **`LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH=1`** if you want cadence tied to chain epochs instead.

**Five-minute defaults (`300` s)** keep miner responses and sandbox verification in a predictable band; they favor capable setups but increase timeouts on slow proofs or cold caches. Operators typically align **`DENDRITE_TIMEOUT_S`**, **`LEAN_VERIFY_TIMEOUT_S`**, **`LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`**, and template difficulty together ([GOVERNANCE.md](GOVERNANCE.md)).

## What can exceed 5 minutes?

- **`LEAN_VERIFY_TIMEOUT_S`** covers **sandbox CPU time** (`lake build`, axiom scan): cold caches, huge imports, or very large generated terms can push compilation near the limit — not “thinking time,” mostly elaboration.
- **`DENDRITE_TIMEOUT_S`** covers **miner HTTP latency** (prover producing `Submission.lean`). Hard problems need more model reasoning tokens; that wall-clock can grow even when Lean verification would be fast once the script exists.

Whether to **keep** very heavy templates is a **subnet governance** choice: harder problems stress miners and verification; easier buckets improve reliability under tight timeouts. Tune timeouts and catalogs together ([GOVERNANCE.md](GOVERNANCE.md)).

## Do validators stay in sync? Do miners get different problems?

**One validator, one round:** every miner this validator **queries** receives the **same** synapse (same theorem). Miners do **not** get different challenges within the same broadcast.

**Across validators:** Lemma maps **`problem_seed_block = (chain_head // N) * N`** with **`LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`** (default **25** ≈ ~5 minutes of Finney blocks). Anyone reading chain head in that window picks the **same** theorem seed ([`epoch.py`](../lemma/validator/epoch.py)). Set **`N=1`** to disable quantization (not recommended for multi-validator subnets).

Within **one** validator process: a round **finishes** query → verify → judge → `set_weights` (if applicable) **before** the next sleep **`LEMMA_VALIDATOR_ROUND_INTERVAL_S`**, so the **next** round does not start until the previous pipeline completes.

## CLI: current theorem and fingerprints

| Command | Purpose |
| ------- | ------- |
| **`lemma status`** | Chain head, **`problem_seed_block`**, theorem id (same rule as validators). |
| **`lemma problems show --current`** | **`Challenge.lean`** after quantizing current head (matches validators). |
| **`lemma problems show --block N`** | Treat **`N`** as chain head height; quantize then sample. |
| **`lemma meta`** | Judge + generated-registry hashes for subnet alignment. |
| **`lemma problems list`** | Only for **`frozen`** catalog mode (enumerate rows). |

## Chutes and billing

[Chutes](https://chutes.ai/) provides OpenAI-compatible HTTP inference. Subscription tiers include credits and caps; usage beyond that is pay-as-you-go. **`DENDRITE_TIMEOUT_S`** is unrelated to provider billing.

**Lemma vs Affine (SN64):** Affine enforces evaluation via Chutes for miners’ committed models. Lemma does not; emissions apply only within the **Lemma subnet**.

## Inference cost (approximate)

Monthly cost ≈ *(answered challenges)* × *($/challenge)*. Cost per challenge depends on token counts and provider **$/M** rates. Measure from logs for realistic estimates.

## Data retention

- No central repository for proofs.
- Validator responses stay **in memory** for the round unless exported.
- Chain stores weights, not full proofs.
- **`LEMMA_TRAINING_EXPORT_JSONL`**: optional append-only local JSONL ([`training_export.py`](../lemma/validator/training_export.py)). Publication requires a separate pipeline (cron, S3, releases).

## Lean verification failures

| `VerifyResult.reason` | Meaning |
| --------------------- | ------- |
| `compile_error` | Build failed |
| `axiom_violation` | Disallowed axioms |
| `cheat_token` | Banned constructs (`sorry`, …) |
| `timeout` / `oom` | Resource limits |
| `docker_error` | Sandbox error |
| `comparator_rejected` | Comparator hook failed |

## Judge protocol

- Prompts: [`prompts.py`](../lemma/judge/prompts.py). Judge returns JSON rubric; parsed in [`json_util.py`](../lemma/judge/json_util.py).
- **`JUDGE_PROVIDER=openai`** means **OpenAI-compatible HTTP**, not necessarily OpenAI Inc.; model ids depend on the server behind `OPENAI_BASE_URL`.
- Align validators with **`uv run lemma meta`** (`judge_profile_sha256`) and optional **`JUDGE_PROFILE_SHA256_EXPECTED`**.

## Miner provenance

Optional **`model_card`** on the synapse labels the reported prover stack for exports (self-reported).

## Validator isolation

Each validator queries miners independently and assigns weights; proofs are not merged across miners.

## Observability

Logs: **`lemma_epoch_summary`**; optional JSONL export. No built-in dashboard ([PRODUCTION.md](PRODUCTION.md)).

## CI templates

[`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py) runs **`lake build`** on templates so Mathlib mismatches fail before release.

## Testnet checklist

1. `uv sync`; `.env` with test endpoint, `NETUID`, wallets.
2. Register keys (`btcli`).
3. Miner: reachable axon; prover keys.
4. Validator: Lean image; `uv run lemma meta`; `uv run lemma validator` (use `--dry-run` / `LEMMA_FAKE_JUDGE=1` when testing).
5. Confirm `set_weights` when ready to write chain.

## Throughput

One **sampled** problem per **validator round** (generated or frozen), not “thousands per minute.” **`DENDRITE_TIMEOUT_S`** bounds a single miner response; round spacing is **`LEMMA_VALIDATOR_ROUND_INTERVAL_S`** (or epoch-aligned if configured above).

## `lemma --help` and Bittensor

`bittensor` is imported lazily in subcommands so the top-level `lemma --help` stays a normal Click help.

## Comparator / lean-eval

Core checks: `lake build` + axiom allowlist + cheat scan. Optional comparator: [COMPARATOR.md](COMPARATOR.md); stricter isolation may follow [lean-eval](https://github.com/leanprover/lean-eval).

## Affine comparison

Affine validators grade miners through a fixed Chutes path. Lemma uses an LLM judge **after** Lean passes; operators choose Anthropic vs OpenAI-compatible endpoints but should **pin one judge configuration** on a live subnet.
