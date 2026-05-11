# Technical Reference

> **New here:** read [litepaper.md](litepaper.md), then follow
> [getting-started.md](getting-started.md). This file is the deeper reference for
> scoring, timeouts, seeds, verifier behavior, model setup, and operations.

## Scoring

Current live path:

1. Lean must typecheck (kernel gate).
2. A passing proof enters scoring; a failing proof does not.
3. Validators turn eligible proofs into weights using the published scoring rules.
4. Same-coldkey hotkeys share that coldkey's allocation instead of multiplying it.

Steps 1-2 are the binary proof-verification gate. Steps 3-4 are downstream
allocation policy; they do not turn invalid proofs into eligible work.

## Known gameability surfaces (plain language)

No subnet is perfectly ungameable; the goal is to make the easiest strategy also the useful one.

- **Predictable problem selection:** if the pool is tiny/static, miners can pre-solve. Mitigation: rotate/expand templates and keep registry upgrades coordinated ([problem-supply-policy.md](problem-supply-policy.md)).
- **Latency and infra advantages:** warm caches and faster hardware can win ties. Mitigation: this is visible/expected operational competition, and correctness still requires Lean.
- **Config drift across validators:** mismatched verifier/scoring config breaks fairness. Mitigation: publish one canonical validator profile and shared env template.

One-line mental model: Lemma rewards Lean-valid proofs.

For the proof-verification design, see [proof-verification-incentives.md](proof-verification-incentives.md). For the active work tracker, see [workplan.md](workplan.md). **Same-coldkey partitioning** is *not* identity verification — see [sybil_economics.md](sybil_economics.md). **Dendrite/Axon + synapse body-hash** — see [transport.md](transport.md).

## Validators querying your axon many times

Each forward is its own response. **Rewards are not a lifetime XP total.** They come from how you **rank in validator rounds where your answer is actually scored** and validators run **`set_weights`**. Doing well in **several** scored rounds can matter across **those** rounds; repeating the same success **offline** does not by itself stack on-chain.

## Prover system prompt (miners)

The miner’s LLM uses the **fixed in-repo** `PROVER_SYSTEM` in [`lemma/miner/prover.py`](../lemma/miner/prover.py) for every prover call (JSON shape and Lean contract). There is **no** env-based append — subnet answers are defined by that prompt plus the challenge text you receive from the protocol.

**Proof only:** miner completions center on **`proof_script`**. Informal reasoning is not part of the live protocol payload. Operators can optionally set **`LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS`** (full `Submission.lean` length; default **off**) to reject overly short scripts — tune so trivial `rfl` goals still pass when unset or low.

## `lemma preview` vs real validator scoring

**`lemma preview`** is a **local** dry run: it calls **your** prover API,
prints the proof script, then runs Lean by default. It does **not** talk to
validators or write scores on-chain. Use **`--no-verify`** when you only want to
see model output.

**`--verify`** (after the LLM returns) runs **`lake build`** **on your machine** to check that `Submission.lean` compiles — the same *kind* of kernel check validators use, but **only locally**:

- **`lemma validator start`:** **`lemma validator start` refuses to run** if **`LEMMA_USE_DOCKER=false`** — validators must use Docker. **`lemma verify`** / miners may still use **`LEMMA_USE_DOCKER=false`** where policy allows (local tooling only).
- **`lemma preview --verify`:** Defaults to the **same Docker sandbox** as validators when **`LEMMA_USE_DOCKER=true`**. Host `lake` is opt-in: **`--host-lean`** or **`LEMMA_PREVIEW_HOST_VERIFY=1`**, and only if **`LEMMA_ALLOW_HOST_LEAN=1`** in **`.env`**.
- **`lemma verify --host-lean`:** Host `lake` only with **`LEMMA_ALLOW_HOST_LEAN=1`**. Otherwise use Docker (default). Still **local**, not on-chain scoring.

To see what validators would sample, use **`lemma status`** / **`lemma problems`**; actual rewards come only when a validator **forwards** to your axon and runs the full round, not from `lemma preview`.

## Validator pipeline (each round)

1. Query miners (`proof_script`).
2. Docker sandbox: `lake build`, axiom policy.
3. If Lean passes: deterministic scoring and weighting.

Miners use a separate prover API to generate proofs.

## Can I use Google Gemini with my personal Google account?

Yes. In [Google AI Studio](https://aistudio.google.com) you can create an API key tied to a normal Google account (subject to Google’s terms and quotas). Gemini exposes an **OpenAI-compatible** HTTP API; see Google’s [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) doc.

For Lemma’s **prover** (miner), use the OpenAI-compatible path: `PROVER_PROVIDER=openai`, set `PROVER_OPENAI_BASE_URL` to Gemini’s OpenAI base URL (see that doc — typically `https://generativelanguage.googleapis.com/v1beta/openai/`), put your Gemini key in **`PROVER_OPENAI_API_KEY`**, and set `PROVER_MODEL` to a Gemini model id (e.g. `gemini-flash-latest` or `gemini-3.1-pro-preview`). Easiest: run **`uv run lemma configure prover`** and choose **`gemini`** — pick vendor first, then API key, then a **tier menu** (Flash / Pro / Lite) or a **custom** Gemini id; the wizard fills in the URL and `PROVER_*`. For other stacks use **Chutes**, **Anthropic**, **OpenAI**, or **custom** (paste base URL) in the same menu. You can still merge keys into `.env` by hand.

**If you see HTTP 404** mentioning `gen-lang-client-…` or `models/... is not found`, you accidentally used a **Google AI Studio internal id** (or a UI-only string) as `PROVER_MODEL`. Replace it with a **public model name** from the [models](https://ai.google.dev/gemini-api/docs/models) list (e.g. `gemini-2.5-flash`), not a `gen-lang-client-*` value.

## Prover retries (`LEMMA_PROVER_LLM_RETRY_ATTEMPTS`)

Default is **4** tries per prover call (exponential backoff on 429 / timeouts / 5xx). Change it for **all** runs via `.env` or `uv run lemma configure prover-retries`. For a **single** `uv run lemma preview` run, use `--retry-attempts N` (1–32). Higher values use more wall-clock; stay within the validator **forward HTTP wait** for mining.

## How much space does the prover get? What does it see?

- **Completion budget:** `LEMMA_PROVER_MAX_TOKENS` caps one JSON response containing the full `Submission.lean`. Default is **32,768** tokens (raise in `.env` if models allow it and your forward HTTP window can tolerate long generations).
- **Prompt contents:** the **user** message to the prover is literally two blocks: a line `Imports hint:` followed by the challenge’s import list (e.g. `["Mathlib"]`), then `Theorem block:` and the full Lean `theorem_statement` string. The **system** message is Lemma’s fixed `PROVER_SYSTEM` (style + JSON contract). There are no other validator-supplied solution steps or hints.
- **Anthropic path:** provider output may still be capped near **8192** tokens per their API for many Claude models even if `LEMMA_PROVER_MAX_TOKENS` is higher.

Correctness of the Lean proof is decided by the **kernel** (sandbox). Passing
proofs can enter live scoring.

## Problem modes

| Mode | Behavior |
| ---- | -------- |
| `LEMMA_PROBLEM_SOURCE=generated` | Block seed → templates ([`generated.py`](../lemma/problems/generated.py)). |
| `frozen` | Rows from `minif2f_frozen.json` — opt-in via **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (see [catalog-sources.md](catalog-sources.md)). |

Template or catalog changes need coordinated upgrades ([governance.md](governance.md)).

## Timeouts

| Variable | Meaning |
| -------- | ------- |
| `LEMMA_BLOCK_TIME_SEC_ESTIMATE` | Rough seconds per chain block; validators derive **forward HTTP wait** = blocks until the next problem-seed edge × this value (then clamped). |
| `LEMMA_FORWARD_WAIT_MIN_S` / `LEMMA_FORWARD_WAIT_MAX_S` | Floor and ceiling for that derived forward HTTP wait (validator client timeout per miner query). |
| `LEMMA_LLM_HTTP_TIMEOUT_S` | HTTP read timeout for one prover completion — must fit within a round’s forward wait at typical chain heads. |
| `LEAN_VERIFY_TIMEOUT_S` | Sandbox `lake build` budget **per miner proof** (default 300 s). |

Validator **round cadence** is not configurable in Lemma: each validator waits for **subnet epoch boundaries** before running `run_epoch` — no wall-clock interval mode.

Timeout values are subnet policy: the operator publishes a single canonical `.env` (or equivalent) and every validator is expected to run that same configuration. Individual validators do not choose different budgets; drift breaks fairness and comparability ([governance.md](governance.md)). Forward HTTP wait follows **block height** (same edge as the next seed rotation), not a single operator-chosen wall-clock cap. If the operator’s published policy includes per-split multipliers (`LEMMA_TIMEOUT_SCALE_BY_SPLIT`, `LEMMA_TIMEOUT_SPLIT_*_MULT`), that is still one policy for the whole subnet, not a per-node setting.

## Miner deadlines vs validator processing (plain English)

**Miners** have an explicit **response** deadline: the synapse **`timeout`** / forward HTTP wait (derived from blocks until the next seed edge × `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, then clamped). If your axon does not complete the HTTP response in time, that round does not count as a successful candidate answer from you.

**Validators** do **not** get a matching global rule like “finish verifying and scoring **every** successful miner before block *N* or before the next theorem.” Lemma picks **one** theorem when `run_epoch` **starts** and runs forward → verify → score for that round; advancing blocks do **not** swap the theorem mid-batch or void in-flight scoring. There is **no** separate “validator batch clock” in addition to the per-proof limits below. You still want fast hardware and tuning so each epoch completes in reasonable wall-clock time and stays competitive with other validators.

**What happens if one proof hits `LEAN_VERIFY_TIMEOUT_S`?** That miner’s Lean step **fails** (verify reason `timeout`). They are **not** verified for the round, so they get **no** proof score and **no** live weight from that proof. Other miners in the same round are unaffected.

Concurrency caps such as **`LEMMA_LEAN_VERIFY_MAX_CONCURRENT`** limit how many proofs are processed at once; extra work **queues**, it is not dropped because the chain moved. With miner attest enabled, **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** trades CPU vs trust — see [validator_lean_load.md](validator_lean_load.md).

## What can exceed the defaults?

Two different clocks:

1. **Forward HTTP wait** (miner → validator)  
   Time the validator’s client will wait for your axon to return the full synapse. It is derived from remaining blocks to the next seed edge × `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, then clamped. This is usually where hard problems burn wall-clock: search, long tactic scripts, retries. Catalog difficulty (easy/medium/hard templates) mostly affects this phase.

2. `LEAN_VERIFY_TIMEOUT_S` (validator sandbox)  
   Time for `lake build` plus axiom/cheat checks on the returned script. The Lean kernel checks proof terms quickly relative to “finding” the proof; elaboration can still be slow when proofs are huge, automation expands large terms, or typeclass inference does heavy work (see the [mathlib overview](https://leanprover-community.github.io/mathlib-overview.html) for topic breadth — e.g. dense algebra, category theory, bundled structures). The first build in a cold Docker layer can also spend minutes downloading or elaborating Mathlib; warm caches behave much better.

   Validators reject `proof_script` payloads over `SYNAPSE_MAX_PROOF_CHARS`
   before scheduling Lean verification.

So: Lean can usually check a correct, modest submission quickly; the risky cases are enormous scripts, pathological elaboration, or cold-cache sandbox cost — not “kernel verification is inherently slow for topology.”

## Why don’t my `.env` changes show up?

Lemma’s settings intentionally load **`.env` after process environment**, so values written by `lemma configure` override stray `export OPENAI_MODEL=...` in your shell. To restore standard pydantic behavior (environment beats `.env`), set `LEMMA_PREFER_PROCESS_ENV=1` (for CI or containers that inject secrets via env only).

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

Within one validator, a round finishes before the code waits for the **next subnet epoch boundary**.

## CLI: current theorem and fingerprints

| Command | Purpose |
| ------- | ------- |
| `lemma status` | Head, seed mode, resolved seed, theorem id. |
| `lemma problems` (or `… show --current`) | `Challenge.lean` for **live** chain head — same rotation as validators. |
| `lemma problems show --block N` | **What-if:** pretend head is `N` (countdown/seed as if at height `N`). |
| `lemma meta` | Validator profile and registry hashes. |
| `lemma problems list` | Frozen catalog only. |

## Chutes and billing

[Chutes](https://chutes.ai/) is OpenAI-compatible HTTP. Forward HTTP wait / `LEMMA_LLM_HTTP_TIMEOUT_S` are not the same as provider billing.

## Inference cost (approximate)

Roughly: (challenges answered) × ($/challenge). Measure from logs.

## Data retention

- No central proof repository.
- Validator responses are in-memory for the round unless exported.
- Chain stores weights, not full proofs.
- `LEMMA_TRAINING_EXPORT_JSONL`: optional local JSONL ([`training_export.py`](../lemma/validator/training_export.py)); **`LEMMA_TRAINING_EXPORT_PROFILE`** controls proof, optional labels, and weights ([training_export.md](training_export.md)).

## Lean verification failures

| `VerifyResult.reason` | Meaning |
| --------------------- | ------- |
| `compile_error` | `lake build` did not succeed or Lean could not run axiom check — **often** Mathlib fetch/build or sandbox limits, not a bad tactic |
| `axiom_violation` | Disallowed axioms |
| `cheat_token` | Banned constructs |
| `timeout` / `oom` | Resource limits |
| `docker_error` | Sandbox error |

**`lemma preview` says FAIL but the proof is just `rfl` on arithmetic literals:** The LLM answer may still be **mathematically fine**. Logs like `no previous manifest`, `creating one from scratch`, `mathlib: running post-update hooks`, then `error: build failed` usually mean **Lake is building Mathlib** (slow), **post-update hooks** failed, **network blocked** (Docker `network_mode=none`), or **timeout** — not that `rfl` is wrong. Fix the **environment** (prebuilt `LEAN_SANDBOX_IMAGE`, `LEAN_SANDBOX_NETWORK=bridge`, higher `LEAN_VERIFY_TIMEOUT_S`) and retry.

## Checking a proof yourself (manual / online)

- **Same setup as Lemma (recommended):** Save your `Submission.lean` to a file and run  
  `lemma verify --problem <theorem-id> --submission path/to/Submission.lean`  
  (e.g. `gen/7037400`). That uses the same Lake workspace + toolchain + Mathlib pin as validators — **no manual Lake setup**.

### [Lean 4 Web](https://live.lean-lang.org/) (“Lean in the browser”)

That site runs Lean **in the browser**; it is **not** the same as Lemma’s Docker/host sandbox. **`import Mathlib` often fails there** (missing Mathlib on the search path, unknown imports, or confusing errors once imports break). That usually reflects **the playground environment**, not whether your proof would pass Lemma’s **Lake + pinned Mathlib** build.

Use it only for **informal** experimentation. For **subnet parity**, use **`lemma verify`** or **`lemma preview --verify`**.

### Older community web editor (Lean 3)

The URL **`leanprover-community.github.io/lean-web-editor`** is a **Lean 3** editor. Lemma uses **Lean 4** + **Mathlib 4**. Paste Lean 4 syntax there and you will get misleading errors — **avoid it** for checking Lemma proofs.

## Validator pipeline

Order matters:

1. **Lean sandbox** — Validators run **`lake build`** on your **`proof_script`** (as `Submission.lean`) together with the challenge, then axiom checks.

2. **Proof scoring** — Only responses that pass Lean enter scoring. A proof
   that fails verification cannot receive a reward score.

So repeated “failures” while you believe the proof is right are usually **environment** (Mathlib fetch, Docker network, cold cache, timeout) or **layout/policy**. The proof has to pass Lean before any reward score exists.

## Miner provenance

Optional `model_card` on the synapse can label a custom prover stack for exports; the built-in miner leaves it unset.

## Validator isolation

Each validator queries miners independently; proofs are not merged across miners.

## Observability

Logs: `lemma_epoch_summary`; optional JSONL. No built-in dashboard ([production.md](production.md)).

## CI templates

[`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py) runs `lake build` on templates.

## Testnet checklist

1. `uv sync --extra btcli`; `.env` with test endpoint, `NETUID`, wallets.
2. Register (`btcli`).
3. Miner: reachable axon; prover keys.
4. Validator: Lean image; `uv run lemma meta`; full validator run without weights: `lemma validator dry-run`.
5. Confirm `set_weights` when ready.

## Throughput

One sampled problem per validator round. The forward HTTP wait (block-derived) bounds one miner response; the next round starts after the **next subnet epoch boundary**.

## `lemma --help` and Bittensor

`bittensor` loads lazily so top-level help stays normal Click output.

## Stricter Lean Isolation

Core: `lake build` + axiom allowlist + cheat scan. Stricter isolation may follow [lean-eval](https://github.com/leanprover/lean-eval) once there is a pinned subnet policy.
