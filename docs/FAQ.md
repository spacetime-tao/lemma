# FAQ

## Scoring

1. Lean must typecheck (kernel gate).
2. Among passing proofs, the LLM judge scores the reasoning trace.
3. Pareto weighting favors better scores and shorter traces ([`pareto.py`](../lemma/scoring/pareto.py)).

## Validator pipeline (each round)

1. Query miners (`proof_script` + reasoning).
2. Docker sandbox: `lake build`, axiom policy, optional comparator (local compute).
3. If Lean passes: judge HTTP (`JUDGE_PROVIDER`, `OPENAI_*`).

Miners use a separate prover API to generate proofs.

## Problem modes

| Mode | Behavior |
| ---- | -------- |
| `LEMMA_PROBLEM_SOURCE=generated` | Block seed → templates ([`generated.py`](../lemma/problems/generated.py)). |
| `frozen` | Rows from `minif2f_frozen.json`. |

Template or catalog changes need coordinated upgrades ([GOVERNANCE.md](GOVERNANCE.md)).

## Timeouts

| Variable | Meaning |
| -------- | ------- |
| `DENDRITE_TIMEOUT_S` | HTTP wait per miner response (default 300 s). |
| `LEAN_VERIFY_TIMEOUT_S` | Sandbox `lake build` budget (default 300 s). |
| `LEMMA_VALIDATOR_ROUND_INTERVAL_S` | Seconds between rounds when not epoch-aligned (default 300). |
| `LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH` | `1` = wait for chain epoch each round; default `0` (timer). |

Timeout values are subnet policy: the operator publishes a single canonical `.env` (or equivalent) and every validator is expected to run that same configuration. Individual validators do not choose different deadlines; drift breaks fairness and comparability ([GOVERNANCE.md](GOVERNANCE.md)). Shipped defaults use one wall-clock for every sampled problem (e.g. 300 s for dendrite and for sandbox). If the operator’s published policy includes per-split multipliers (`LEMMA_TIMEOUT_SCALE_BY_SPLIT`, `LEMMA_TIMEOUT_SPLIT_*_MULT`), that is still one policy for the whole subnet, not a per-node setting.

## What can exceed the defaults?

Two different clocks:

1. `DENDRITE_TIMEOUT_S` (miner → validator)  
   Time for the prover / LLM to return `Submission.lean`. This is usually where hard problems burn wall-clock: search, long tactic scripts, retries. Catalog difficulty (easy/medium/hard templates) mostly affects this phase.

2. `LEAN_VERIFY_TIMEOUT_S` (validator sandbox)  
   Time for `lake build` plus axiom/cheat checks on the returned script. The Lean kernel checks proof terms quickly relative to “finding” the proof; elaboration can still be slow when proofs are huge, automation expands large terms, or typeclass inference does heavy work (see the [mathlib overview](https://leanprover-community.github.io/mathlib-overview.html) for topic breadth — e.g. dense algebra, category theory, bundled structures). The first build in a cold Docker layer can also spend minutes downloading or elaborating Mathlib; warm caches behave much better.

So: Lean can usually check a correct, modest submission quickly; the risky cases are enormous scripts, pathological elaboration, or cold-cache sandbox cost — not “kernel verification is inherently slow for topology.”

## Which math areas tend to strain a tight miner deadline?

Rough guide for generation time (model writing tactics), not a statement that Mathlib cannot formalize these topics:

- Combinatorics / graph theory / Ramsey-style arguments — many cases, constructions, or lemmas chained in one proof.
- Inequalities and estimates (analysis, special functions) — long `calc` or `linarith` / `nlinarith` chains; epsilon–delta bookkeeping.
- Algebra / field theory / Galois-style arguments — multi-step non-routine steps unless the template guides the skeleton.
- Number theory (beyond short congruence tricks) — longer intermediate lemmas.
- Heavy imports and abstraction — algebraic geometry (schemes, spectral spaces), representation theory, homological algebra can slow elaboration if the generated proof pulls in big libraries and large proof terms.

Often easier under a short miner clock: small linear algebra exercises, single-lemma group or ring facts, one-off analysis goals that automation handles (`norm_num`, decidability, short `calc` chains), when the template matches those tactics.

Subnet policy and catalog design decide what appears in challenges; the operator balances difficulty against the published `DENDRITE_TIMEOUT_S` and `LEAN_VERIFY_TIMEOUT_S`.

## Sync across validators

One validator, one round: every queried miner gets the same synapse.

Across validators: default `LEMMA_PROBLEM_SEED_MODE=subnet_epoch` uses subnet Tempo so nodes with the same chain head and `NETUID` agree on seed. `quantize` uses `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`. Same code, problem source, registry hashes, and consistent RPC matter.

Within one validator, a round finishes before the next sleep (`LEMMA_VALIDATOR_ROUND_INTERVAL_S`).

## CLI: current theorem and fingerprints

| Command | Purpose |
| ------- | ------- |
| `lemma status` | Head, seed mode, resolved seed, theorem id. |
| `lemma problems show --current` | `Challenge.lean` for current resolution. |
| `lemma problems show --block N` | Resolve as if head were `N`. |
| `lemma meta` | Judge + registry hashes. |
| `lemma problems list` | Frozen catalog only. |

## Chutes and billing

[Chutes](https://chutes.ai/) is OpenAI-compatible HTTP. `DENDRITE_TIMEOUT_S` is not provider billing.

Lemma vs Affine (SN64): Affine ties miners to Chutes for evaluation; Lemma subnet emissions are independent.

## Inference cost (approximate)

Roughly: (challenges answered) × ($/challenge). Measure from logs.

## Data retention

- No central proof repository.
- Validator responses are in-memory for the round unless exported.
- Chain stores weights, not full proofs.
- `LEMMA_TRAINING_EXPORT_JSONL`: optional local JSONL ([`training_export.py`](../lemma/validator/training_export.py)).

## Lean verification failures

| `VerifyResult.reason` | Meaning |
| --------------------- | ------- |
| `compile_error` | Build failed |
| `axiom_violation` | Disallowed axioms |
| `cheat_token` | Banned constructs |
| `timeout` / `oom` | Resource limits |
| `docker_error` | Sandbox error |
| `comparator_rejected` | Comparator hook failed |

## Judge protocol

- Prompts: [`prompts.py`](../lemma/judge/prompts.py); parsing [`json_util.py`](../lemma/judge/json_util.py).
- `JUDGE_PROVIDER=openai` means OpenAI-compatible HTTP; model ids depend on `OPENAI_BASE_URL`.
- Align with `uv run lemma meta` and optional `JUDGE_PROFILE_SHA256_EXPECTED`.

## Miner provenance

Optional `model_card` on the synapse labels the prover stack for exports.

## Validator isolation

Each validator queries miners independently; proofs are not merged across miners.

## Observability

Logs: `lemma_epoch_summary`; optional JSONL. No built-in dashboard ([PRODUCTION.md](PRODUCTION.md)).

## CI templates

[`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py) runs `lake build` on templates.

## Testnet checklist

1. `uv sync`; `.env` with test endpoint, `NETUID`, wallets.
2. Register (`btcli`).
3. Miner: reachable axon; prover keys.
4. Validator: Lean image; `uv run lemma meta`; `uv run lemma validator` (`--dry-run`, `LEMMA_FAKE_JUDGE=1` when testing).
5. Confirm `set_weights` when ready.

## Throughput

One sampled problem per validator round. `DENDRITE_TIMEOUT_S` bounds one miner response; spacing is `LEMMA_VALIDATOR_ROUND_INTERVAL_S` or epoch alignment.

## `lemma --help` and Bittensor

`bittensor` loads lazily so top-level help stays normal Click output.

## Comparator / lean-eval

Core: `lake build` + axiom allowlist + cheat scan. Optional: [COMPARATOR.md](COMPARATOR.md); stricter isolation may follow [lean-eval](https://github.com/leanprover/lean-eval).

## Affine comparison

Affine validators grade via a fixed Chutes path. Lemma judges after Lean passes; operators should pin one judge stack on a live subnet.
