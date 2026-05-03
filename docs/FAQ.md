# FAQ

## Scoring

1. Lean must typecheck (kernel gate).
2. Among passing proofs, the LLM judge scores the reasoning trace.
3. Pareto weighting favors better scores and shorter traces ([`pareto.py`](../lemma/scoring/pareto.py)).

## Validators querying your axon many times

Each forward is its own response. **Rewards are not a lifetime XP total.** They come from how you **rank in validator rounds where your answer is actually scored** and validators run **`set_weights`**. Doing well in **several** scored rounds can matter across **those** rounds; repeating the same success **offline** does not by itself stack on-chain.

## `LEMMA_PROVER_SYSTEM_APPEND` — what, where, why

**What:** Extra **natural-language instructions** you choose (audience, style, language, emphasis). Lemma **appends** them after the fixed in-repo `PROVER_SYSTEM` that defines the JSON contract (`reasoning_steps`, `proof_script`, no `sorry`, etc.). You are **not** replacing that contract — only adding operator policy on top.

**Where:** `LEMMA_PROVER_SYSTEM_APPEND` in `.env`. Prefer **`lemma configure prover-system-append`** (opens an editor or accepts `--file` / `--clear`) so you do not have to hand-edit multiline text.

**Why:** Steers how the model writes **without** forking the repo prompt. Saved **Gemini / ChatGPT “system instructions” in the browser UI are not sent** to Lemma’s HTTP calls unless you put equivalent text here (or maintain your own fork of `PROVER_SYSTEM`).

**Informal vs Lean:** The miner prover makes **one** LLM completion per challenge. The **system** message (built-in + append) influences **both** informal **`reasoning_steps`** **and** the **`proof_script`** string (the Lean file contents). There is no separate env var for “informal only.” **Correctness** of the Lean proof is still enforced by the **kernel** in the validator sandbox; append cannot disable that. Tweaking append **can** improve judged exposition and sometimes helps the model produce valid proofs, but it is not a substitute for model choice, temperature, timeouts, or Mathlib skill.

**Detailed formal proofs:** The built-in `PROVER_SYSTEM` instructs the model to write **expanded** `by` blocks (`calc`, induction branches, `--` comments), not one-line opaque tactics when the math naturally has multiple steps. Operators can optionally set **`LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS`** (full `Submission.lean` character count; default **off**) to reject overly short scripts and force retries toward longer proofs — tune carefully so trivial `rfl`-only goals still pass when the minimum is unset or low.

## Can tweaking the prover system append improve scores?

Sometimes. Clearer, rubric-aligned reasoning often scores better with the judge; a more disciplined prompt can also reduce malformed JSON or weak proofs — but outcomes still depend on the **model**, **temperature**, **timeouts**, and the **theorem**. Use **`lemma configure prover-system-append`** for a visible, CLI-first path; compare with `lemma try-prover` before relying on it under validator forward wait.

## Validator pipeline (each round)

1. Query miners (`proof_script` + reasoning).
2. Docker sandbox: `lake build`, axiom policy, optional comparator (local compute).
3. If Lean passes: judge HTTP (`JUDGE_PROVIDER`, `OPENAI_*`).

Miners use a separate prover API to generate proofs.

## Can I use Google Gemini with my personal Google account?

Yes. In [Google AI Studio](https://aistudio.google.com) you can create an API key tied to a normal Google account (subject to Google’s terms and quotas). Gemini exposes an **OpenAI-compatible** HTTP API; see Google’s [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) doc.

For Lemma’s **prover** (miner), use the OpenAI-compatible path: `PROVER_PROVIDER=openai`, set `OPENAI_BASE_URL` to Gemini’s OpenAI base URL (see that doc — typically `https://generativelanguage.googleapis.com/v1beta/openai/`), put your Gemini key in `OPENAI_API_KEY`, and set `PROVER_MODEL` to a Gemini model id (e.g. `gemini-2.0-flash` or whatever the docs list). You can run `lemma configure prover` and choose **custom OpenAI-compatible**, or merge those keys into `.env`. Validators use a **separate** judge configuration (`JUDGE_PROVIDER`, `OPENAI_MODEL`, …); do not confuse prover and judge env vars.

**If you see HTTP 404** mentioning `gen-lang-client-…` or `models/... is not found`, you accidentally used a **Google AI Studio internal id** (or a UI-only string) as `PROVER_MODEL`. Replace it with a **public model name** from the [models](https://ai.google.dev/gemini-api/docs/models) list (e.g. `gemini-2.0-flash`), not a `gen-lang-client-*` value.

## Prover retries (`LEMMA_PROVER_LLM_RETRY_ATTEMPTS`)

Default is **4** tries per prover call (exponential backoff on 429 / timeouts / 5xx). Change it for **all** runs via `.env` or `lemma configure prover-retries`. For a **single** `lemma try-prover` run, use `--retry-attempts N` (1–32). Higher values use more wall-clock; stay within the validator **forward HTTP wait** for mining.

## How much space does the prover get? What does it see?

- **Completion budget:** `LEMMA_PROVER_MAX_TOKENS` caps one JSON response (informal reasoning + full `Submission.lean`). Default is **32,768** tokens (raise in `.env` if models allow it and your forward HTTP window can tolerate long generations).
- **Prompt contents:** the **user** message to the prover is literally two blocks: a line `Imports hint:` followed by the challenge’s import list (e.g. `["Mathlib"]`), then `Theorem block:` and the full Lean `theorem_statement` string. The **system** message is Lemma’s fixed `PROVER_SYSTEM` (style + JSON contract). There are no other validator-supplied solution steps or hints.
- **Anthropic path:** provider output may still be capped near **8192** tokens per their API for many Claude models even if `LEMMA_PROVER_MAX_TOKENS` is higher.

Correctness of the Lean proof is decided by the **kernel** (sandbox). The **LLM judge** scores only the informal trace (`coherence`, `exploration`, `clarity`). The rubric is written so **long** traces and **long** proofs are allowed when substantive; padding without insight still scores lower.

Among miners with **similar** judge scores, weighting still prefers **shorter** reasoning text when comparing candidates (Pareto tradeoff on score vs length). That encourages concise clarity among ties; it does not ask the judge to punish length by itself.

## `reasoning_steps` vs `reasoning_trace` (plain English)

Think of **informal reasoning** as “explain your math before the Lean file.” You deliver that explanation in **one** structured form:

- **`reasoning_steps`** (required): a JSON **array** of steps. Each step is one chunk of explanation — usually many entries so it reads step-by-step (induction base vs step, each `calc` line, etc.). This is what validators and judges consume first-class.

**`reasoning_trace`** was an **older** shortcut: one **single string** holding *all* informal text mashed together. We **do not** ask miners to supply **both**. New rule: **only `reasoning_steps` counts.** If the model sends informal content **only** as `reasoning_trace` and skips `reasoning_steps`, Lemma treats that as **missing informal reasoning** — the submission is **rejected at policy** (stub proof so Lean verify fails; no reward path from skipping the structured narrative).

**Fairness:** everyone must produce **(1)** non-empty structured informal steps and **(2)** a real `proof_script`. Skipping (1) or submitting blank steps is **not** allowed.

## Problem modes

| Mode | Behavior |
| ---- | -------- |
| `LEMMA_PROBLEM_SOURCE=generated` | Block seed → templates ([`generated.py`](../lemma/problems/generated.py)). |
| `frozen` | Rows from `minif2f_frozen.json`. |

Template or catalog changes need coordinated upgrades ([GOVERNANCE.md](GOVERNANCE.md)).

## Timeouts

| Variable | Meaning |
| -------- | ------- |
| `LEMMA_BLOCK_TIME_SEC_ESTIMATE` | Rough seconds per chain block; validators derive **forward HTTP wait** = blocks until the next problem-seed edge × this value (then clamped). |
| `LEMMA_FORWARD_WAIT_MIN_S` / `LEMMA_FORWARD_WAIT_MAX_S` | Floor and ceiling for that derived forward HTTP wait (validator client timeout per miner query). |
| `LEMMA_LLM_HTTP_TIMEOUT_S` | HTTP read timeout for one prover or judge completion — must fit within a round’s forward wait at typical chain heads. |
| `LEAN_VERIFY_TIMEOUT_S` | Sandbox `lake build` budget (default 300 s). |
| `LEMMA_VALIDATOR_ROUND_INTERVAL_S` | Seconds between rounds when not epoch-aligned (default 300). |
| `LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH` | `1` = wait for chain epoch each round; default `0` (timer). |

Timeout values are subnet policy: the operator publishes a single canonical `.env` (or equivalent) and every validator is expected to run that same configuration. Individual validators do not choose different budgets; drift breaks fairness and comparability ([GOVERNANCE.md](GOVERNANCE.md)). Forward HTTP wait follows **block height** (same edge as the next seed rotation), not a single operator-chosen wall-clock cap. If the operator’s published policy includes per-split multipliers (`LEMMA_TIMEOUT_SCALE_BY_SPLIT`, `LEMMA_TIMEOUT_SPLIT_*_MULT`), that is still one policy for the whole subnet, not a per-node setting.

## What can exceed the defaults?

Two different clocks:

1. **Forward HTTP wait** (miner → validator)  
   Time the validator’s client will wait for your axon to return the full synapse. It is derived from remaining blocks to the next seed edge × `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, then clamped. This is usually where hard problems burn wall-clock: search, long tactic scripts, retries. Catalog difficulty (easy/medium/hard templates) mostly affects this phase.

2. `LEAN_VERIFY_TIMEOUT_S` (validator sandbox)  
   Time for `lake build` plus axiom/cheat checks on the returned script. The Lean kernel checks proof terms quickly relative to “finding” the proof; elaboration can still be slow when proofs are huge, automation expands large terms, or typeclass inference does heavy work (see the [mathlib overview](https://leanprover-community.github.io/mathlib-overview.html) for topic breadth — e.g. dense algebra, category theory, bundled structures). The first build in a cold Docker layer can also spend minutes downloading or elaborating Mathlib; warm caches behave much better.

So: Lean can usually check a correct, modest submission quickly; the risky cases are enormous scripts, pathological elaboration, or cold-cache sandbox cost — not “kernel verification is inherently slow for topology.”

## Why doesn’t my judge model match what `lemma setup` wrote?

Lemma’s settings intentionally load **`.env` after process environment**, so values written by `lemma configure` / `merge_dotenv` override stray `export OPENAI_MODEL=...` in your shell. To restore standard pydantic behavior (environment beats `.env`), set `LEMMA_PREFER_PROCESS_ENV=1` (for CI or containers that inject secrets via env only).

## Which math areas tend to strain a tight miner deadline?

Rough guide for generation time (model writing tactics), not a statement that Mathlib cannot formalize these topics:

- Combinatorics / graph theory / Ramsey-style arguments — many cases, constructions, or lemmas chained in one proof.
- Inequalities and estimates (analysis, special functions) — long `calc` or `linarith` / `nlinarith` chains; epsilon–delta bookkeeping.
- Algebra / field theory / Galois-style arguments — multi-step non-routine steps unless the template guides the skeleton.
- Number theory (beyond short congruence tricks) — longer intermediate lemmas.
- Heavy imports and abstraction — algebraic geometry (schemes, spectral spaces), representation theory, homological algebra can slow elaboration if the generated proof pulls in big libraries and large proof terms.

Often easier under a short miner clock: small linear algebra exercises, single-lemma group or ring facts, one-off analysis goals that automation handles (`norm_num`, decidability, short `calc` chains), when the template matches those tactics.

Subnet policy and catalog design decide what appears in challenges; the operator balances difficulty against the published block-time / forward-wait clamps and `LEAN_VERIFY_TIMEOUT_S`.

## Sync across validators

One validator, one round: every queried miner gets the same synapse.

Across validators: default `LEMMA_PROBLEM_SEED_MODE=quantize` rotates the shared theorem every `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` (default **100** blocks; at ~12 s/block that is about **20 minutes** per theorem). Subnet operators may switch to `subnet_epoch` to follow on-chain Tempo instead. Same code, problem source, registry hashes, and consistent RPC matter.

Within one validator, a round finishes before the next sleep (`LEMMA_VALIDATOR_ROUND_INTERVAL_S`).

## CLI: current theorem and fingerprints

| Command | Purpose |
| ------- | ------- |
| `lemma status` | Head, seed mode, resolved seed, theorem id. |
| `lemma problems` (or `… show --current`) | `Challenge.lean` for **live** chain head — same rotation as validators. |
| `lemma problems show --block N` | **What-if:** pretend head is `N` (countdown/seed as if at height `N`). |
| `lemma meta` | Judge + registry hashes. |
| `lemma problems list` | Frozen catalog only. |

## Chutes and billing

[Chutes](https://chutes.ai/) is OpenAI-compatible HTTP. Forward HTTP wait / `LEMMA_LLM_HTTP_TIMEOUT_S` are not the same as provider billing.

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
| `compile_error` | `lake build` did not succeed or Lean could not run axiom check — **often** Mathlib fetch/build or sandbox limits, not a bad tactic |
| `axiom_violation` | Disallowed axioms |
| `cheat_token` | Banned constructs |
| `timeout` / `oom` | Resource limits |
| `docker_error` | Sandbox error |
| `comparator_rejected` | Comparator hook failed |

**`try-prover` says FAIL but the proof is just `rfl` on arithmetic literals:** The LLM answer may still be **mathematically fine**. Logs like `no previous manifest`, `creating one from scratch`, `mathlib: running post-update hooks`, then `error: build failed` usually mean **Lake is building Mathlib** (slow), **post-update hooks** failed, **network blocked** (Docker `network_mode=none`), or **timeout** — not that `rfl` is wrong. Fix the **environment** (prebuilt `LEAN_SANDBOX_IMAGE`, `LEAN_SANDBOX_NETWORK=bridge`, higher `LEAN_VERIFY_TIMEOUT_S`) and retry.

## Checking a proof yourself (manual / online)

- **Same setup as Lemma (recommended):** Save your `Submission.lean` to a file and run  
  `lemma verify --problem <theorem-id> --submission path/to/Submission.lean`  
  (e.g. `gen/7037400`). That uses the same Lake workspace + toolchain + Mathlib pin as validators — **no manual Lake setup**.

### [Lean 4 Web](https://live.lean-lang.org/) (“Lean in the browser”)

That site runs Lean **in the browser**; it is **not** the same as Lemma’s Docker/host sandbox. **`import Mathlib` often fails there** (missing Mathlib on the search path, unknown imports, or confusing errors once imports break). That usually reflects **the playground environment**, not whether your proof would pass Lemma’s **Lake + pinned Mathlib** build.

Use it only for **informal** experimentation. For **subnet parity**, use **`lemma verify`** or **`lemma try-prover --verify`**.

### Older community web editor (Lean 3)

The URL **`leanprover-community.github.io/lean-web-editor`** is a **Lean 3** editor. Lemma uses **Lean 4** + **Mathlib 4**. Paste Lean 4 syntax there and you will get misleading errors — **avoid it** for checking Lemma proofs.

## Validator pipeline: Lean kernel vs LLM judge

Order matters:

1. **Lean sandbox** — Validators run **`lake build`** on your **`proof_script`** (as `Submission.lean`) together with the challenge, then axiom checks. **If this fails (`compile_error`, timeout, etc.), the judge is not used** for scoring that response — the failure is **not** “the judge disagreed.”

2. **Judge LLM** — Only for responses that **passed Lean**, the validator calls the **judge** model to score **informal reasoning** (and sees your proof text). The judge **does not execute Lean again**.

So repeated “failures” while you believe the proof is right are usually **environment** (Mathlib fetch, Docker network, cold cache, timeout) or **layout/policy** — until Lean passes, the judge never weighs in.

## Judge protocol

- Prompts: [`prompts.py`](../lemma/judge/prompts.py); parsing [`json_util.py`](../lemma/judge/json_util.py).
- `JUDGE_PROVIDER=openai` means OpenAI-compatible HTTP. **Validators** must use `OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2-TEE` (Chutes id) unless `LEMMA_ALLOW_NONCANONICAL_JUDGE_MODEL=1` for experiments.
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

One sampled problem per validator round. The forward HTTP wait (block-derived) bounds one miner response; spacing is `LEMMA_VALIDATOR_ROUND_INTERVAL_S` or epoch alignment.

## `lemma --help` and Bittensor

`bittensor` loads lazily so top-level help stays normal Click output.

## Comparator / lean-eval

Core: `lake build` + axiom allowlist + cheat scan. Optional: [COMPARATOR.md](COMPARATOR.md); stricter isolation may follow [lean-eval](https://github.com/leanprover/lean-eval).

## Affine comparison

Affine validators grade via a fixed Chutes path. Lemma judges after Lean passes; operators should pin one judge stack on a live subnet.
