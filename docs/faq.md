# FAQ

New here? Start with [getting-started.md](getting-started.md).

This page answers common questions about scoring, timing, proofs, and local
checks.

## Scoring

The live path is:

1. Miner returns `proof_script`.
2. Validator checks it with Lean.
3. Passing proofs enter scoring.
4. Failing proofs do not enter scoring.
5. Same-coldkey hotkeys share that coldkey's allocation.

One-line model: Lemma rewards Lean-valid proofs.

More detail: [proof-verification-incentives.md](proof-verification-incentives.md).

## What Can Be Gamed?

No subnet is perfectly hard to game. Lemma tries to make useful work the easiest
way to earn.

Known risks:

- Small problem pools can be pre-solved. Keep problem supply growing.
- Warm caches and fast hardware can help. That is expected operations work.
- Validators with different configs can be unfair. Publish one profile.

Same-coldkey partitioning is not identity proof. See
[sybil_economics.md](sybil_economics.md).

## Why Do Validators Query My Axon Many Times?

Each query is one chance to answer one round.

Rewards are not lifetime points. They come from validator rounds where your
answer is scored and validators run `set_weights`.

## What Prompt Does The Miner Use?

The miner uses the fixed `PROVER_SYSTEM` in
[`lemma/miner/prover.py`](../lemma/miner/prover.py).

There is no `.env` prompt append.

The live payload centers on `proof_script`. Informal reasoning is not part of
live reward scoring.

## Is `lemma-cli try-prover --verify` Real Scoring?

No.

`lemma-cli try-prover` is a local prover test. It does not talk to validators and
does not write weights.

`lemma-cli rehearsal` runs the local prover plus Lean path. It is closer to a
real round, but it is still local.

Live rewards only happen when a validator forwards to your axon and scores the
round.

## What Does `--verify` Do?

After the model returns, `--verify` checks `Submission.lean` on your machine.

It uses the same kind of Lean check validators use. It is still local.

Production validators must use Docker. Host Lean is only for local debugging
when policy allows it.

## Can I Use Gemini?

Yes. Gemini has an OpenAI-compatible API.

Use:

- `PROVER_PROVIDER=openai`
- `PROVER_OPENAI_BASE_URL` set to Gemini's OpenAI-compatible URL
- `PROVER_OPENAI_API_KEY` set to your Gemini key
- `PROVER_MODEL` set to a public Gemini model id

The easiest path is:

```bash
uv run lemma-cli configure prover
```

Do not use Google AI Studio internal ids such as `gen-lang-client-*`. Use public
model names from Google's model list.

## Prover Retries

`LEMMA_PROVER_LLM_RETRY_ATTEMPTS` defaults to `4`.

Retries help with 429s, timeouts, and 5xx errors. More retries use more
wall-clock time. Keep them inside the validator forward wait.

For one local run:

```bash
uv run lemma-cli try-prover --retry-attempts N
```

## What Does The Prover See?

The user message has two blocks:

- `Imports hint:`
- `Theorem block:`

The response must contain the full `Submission.lean`.

`LEMMA_PROVER_MAX_TOKENS` caps the response size. The default is `32768`.

## Problem Modes

| Mode | Meaning |
| --- | --- |
| `generated` | Block seed maps to generated templates. |
| `frozen` | Rows from `minif2f_frozen.json`; dev opt-in only. |

Template and catalog changes need coordinated upgrades. See
[governance.md](governance.md).

## Timeouts

| Variable | Meaning |
| --- | --- |
| `LEMMA_BLOCK_TIME_SEC_ESTIMATE` | Rough seconds per block. |
| `LEMMA_FORWARD_WAIT_MIN_S` / `LEMMA_FORWARD_WAIT_MAX_S` | Bounds for miner response wait. |
| `LEMMA_LLM_HTTP_TIMEOUT_S` | Timeout for one prover completion. |
| `LEAN_VERIFY_TIMEOUT_S` | Lean sandbox time per proof. |

Validator cadence follows subnet epoch boundaries. It is not a local timer.

Timeouts are subnet policy. Validators should use the same values.

## Miner Deadline vs Validator Work

Miners have a response deadline: the synapse `timeout`.

Validators do not throw away an in-flight batch just because blocks advanced.
They finish the round they started.

If one proof hits `LEAN_VERIFY_TIMEOUT_S`, that proof fails for that round. Other
miners in the round are not affected.

Concurrency caps limit how many proofs run at once. Extra proof checks queue.

## What Can Exceed The Defaults?

Two clocks matter:

1. Miner response wait: finding and returning the proof.
2. Lean verify timeout: checking the returned script.

Slow cases include large scripts, hard elaboration, cold Docker caches, and heavy
Mathlib work.

## Why Don't My `.env` Changes Show Up?

Lemma loads `.env` after process environment by default. This lets
`lemma-cli configure` override stray shell exports.

To make process environment win, set:

```bash
LEMMA_PREFER_PROCESS_ENV=1
```

## Which Math Areas Are Hard Under Short Deadlines?

Often harder:

- combinatorics and graph theory;
- long inequalities;
- non-routine algebra;
- number theory beyond short congruence tricks;
- heavy imports and abstraction.

Often easier:

- short linear algebra;
- single-lemma group or ring facts;
- small arithmetic goals;
- proofs handled by `norm_num`, `linarith`, or short `calc` chains.

Subnet policy decides which problems appear.

## Sync Across Validators

One validator round sends the same synapse to every queried miner.

Across validators, the default `LEMMA_PROBLEM_SEED_MODE=quantize` rotates the
shared theorem every `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`.

Validators should share code, problem source, registry hashes, and RPC policy.

## Useful CLI Commands

| Command | Purpose |
| --- | --- |
| `lemma-cli status` | Head, seed mode, seed, theorem id. |
| `lemma-cli problems` | Current live theorem. |
| `lemma-cli problems show --block N` | What would be live at block `N`. |
| `lemma meta` | Validator profile and registry hashes. |
| `lemma-cli problems list` | Frozen catalog only. |

## Data Retention

- There is no central proof repository.
- Validator responses live in memory unless exported.
- The chain stores weights, not full proofs.
- `LEMMA_TRAINING_EXPORT_JSONL` can write local JSONL.

See [training_export.md](training_export.md).

## Lean Verification Failures

| Reason | Meaning |
| --- | --- |
| `compile_error` | `lake build` failed or axiom check could not run. |
| `axiom_violation` | Disallowed axioms. |
| `cheat_token` | Banned constructs. |
| `timeout` / `oom` | Resource limits. |
| `docker_error` | Sandbox error. |

If a simple proof fails while Mathlib is building, the environment may be the
problem. Prebuild the Lean image, use a warm cache, and retry.

## Checking A Proof Yourself

Use Lemma's verifier when possible:

```bash
lemma verify --problem <theorem-id> --submission path/to/Submission.lean
```

This uses Lemma's Lake workspace, Lean toolchain, and Mathlib pin.

Lean 4 Web is useful for experiments, but it is not the same as Lemma's sandbox.
The old Lean web editor is Lean 3 and should not be used for Lemma proofs.

## Validator Pipeline

1. Lean sandbox checks `proof_script` as `Submission.lean`.
2. A passing proof enters scoring.
3. A failing proof receives no proof score.

Most confusing failures are environment, cache, timeout, or policy issues. The
proof still has to pass Lean before any reward score exists.
