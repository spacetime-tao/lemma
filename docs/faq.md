# FAQ

> **New here:** follow [getting-started](getting-started.md) first (install, keys, miner, validator). This file is long-form reference: scoring, timeouts, seeds, policy.

## Scoring

1. Lean must typecheck (kernel gate).
2. Among passing proofs, the LLM judge scores the reasoning trace.
3. Pareto weighting favors better scores and shorter traces ([`pareto.py`](../lemma/scoring/pareto.py)).

## Known gameability surfaces (plain language)

No subnet is perfectly ungameable; the goal is to make the easiest strategy also the useful one.

- **Predictable problem selection:** if the pool is tiny/static, miners can pre-solve. Mitigation: rotate/expand templates and keep registry upgrades coordinated.
- **Prompt injection in miner traces:** miners can write manipulative text, but it is untrusted input. Mitigation: Lean pass is required first, judge uses a fixed rubric/schema, and validators keep judge stack pins aligned.
- **Latency and infra advantages:** warm caches and faster hardware can win ties. Mitigation: this is visible/expected operational competition, and correctness still requires Lean.
- **Judge-style over-optimization:** miners may tune wording for rubric points. Mitigation: Pareto combines rubric with brevity and operators can evolve rubric/profile hashes.
- **Config drift across validators:** mismatched judge/model/config breaks fairness. Mitigation: publish one canonical stack and enforce `JUDGE_PROFILE_SHA256_EXPECTED`.

One-line mental model: public deterministic rules are okay; you still need correct Lean proofs and strong judged reasoning under the same pinned validator policy.

For post-audit scoring changes (proof/judge blend, dedup, EMA, multi-theorem epochs, reserved protocol flags), see [incentive_migration.md](incentive_migration.md). For a **living checklist** of shipped items and known gaps, see [incentive-roadmap.md](incentive-roadmap.md).

## Validators querying your axon many times

Each forward is its own response. **Rewards are not a lifetime XP total.** They come from how you **rank in validator rounds where your answer is actually scored** and validators run **`set_weights`**. Doing well in **several** scored rounds can matter across **those** rounds; repeating the same success **offline** does not by itself stack on-chain.

## Prover system prompt (miners)

The miner’s LLM uses the **fixed in-repo** `PROVER_SYSTEM` in [`lemma/miner/prover.py`](../lemma/miner/prover.py) for every prover call (JSON shape, reasoning rules, Lean contract). There is **no** env-based append — subnet answers are defined by that prompt plus the challenge text you receive from the protocol.

**Informal vs Lean:** One completion fills both **`reasoning_steps`** and **`proof_script`**. **Detailed formal proofs:** The built-in prompt asks for expanded `by` blocks where appropriate. Operators can optionally set **`LEMMA_PROVER_MIN_PROOF_SCRIPT_CHARS`** (full `Submission.lean` length; default **off**) to reject overly short scripts — tune so trivial `rfl` goals still pass when unset or low.

## `lemma try-prover --verify` vs real validator scoring

**`lemma try-prover`** is a **local** dry run: it calls **your** prover API and prints output. It does **not** talk to validators or write scores on-chain.

**`lemma rehearsal`** chains the same prover + Lean path (defaults match **`lemma try-prover --verify`**) and then calls **your judge** on the informal trace + `Submission.lean` — still local, still no axon / no `set_weights`, but closer to how a scored forward feels.

**`--verify`** (after the LLM returns) runs **`lake build`** **on your machine** to check that `Submission.lean` compiles — the same *kind* of kernel check validators use, but **only locally**:

- **`lemma validator`:** **`lemma validator` refuses to start** if **`LEMMA_USE_DOCKER=false`** — validators must use Docker. **`lemma verify`** / miners may still use **`LEMMA_USE_DOCKER=false`** where policy allows (local tooling only).
- **`try-prover --verify`:** Defaults to the **same Docker sandbox** as validators when **`LEMMA_USE_DOCKER=true`**. Host `lake` is opt-in: **`--host-lean`** or **`LEMMA_TRY_PROVER_HOST_VERIFY=1`**, and only if **`LEMMA_ALLOW_HOST_LEAN=1`** in **`.env`**.
- **`lemma verify --host-lean`:** Host `lake` only with **`LEMMA_ALLOW_HOST_LEAN=1`**. Otherwise use Docker (default). Still **local**, not on-chain scoring.

To see what validators would sample, use **`lemma status`** / **`lemma problems`**; actual rewards come only when a validator **forwards** to your axon and runs the full round (Lean + judge), not from `try-prover` or `rehearsal`.

## Validator pipeline (each round)

1. Query miners (`proof_script` + reasoning).
2. Docker sandbox: `lake build`, axiom policy, optional comparator (local compute).
3. If Lean passes: judge HTTP (`JUDGE_PROVIDER`, `OPENAI_*`).

Miners use a separate prover API to generate proofs.

## Can I use Google Gemini with my personal Google account?

Yes. In [Google AI Studio](https://aistudio.google.com) you can create an API key tied to a normal Google account (subject to Google’s terms and quotas). Gemini exposes an **OpenAI-compatible** HTTP API; see Google’s [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) doc.

For Lemma’s **prover** (miner), use the OpenAI-compatible path: `PROVER_PROVIDER=openai`, set `PROVER_OPENAI_BASE_URL` to Gemini’s OpenAI base URL (see that doc — typically `https://generativelanguage.googleapis.com/v1beta/openai/`), put your Gemini key in **`PROVER_OPENAI_API_KEY`**, and set `PROVER_MODEL` to a Gemini model id (e.g. `gemini-flash-latest` or `gemini-3.1-pro-preview`). Easiest: run **`lemma configure prover`** and choose **`gemini`** — pick vendor first, then API key, then a **tier menu** (Flash / Pro / Lite) or a **custom** Gemini id; the wizard fills in the URL and `PROVER_*`. For other stacks use **Chutes**, **Anthropic**, **OpenAI**, or **custom** (paste base URL) in the same menu. You can still merge keys into `.env` by hand. Validators use a **separate** judge stack: **`JUDGE_OPENAI_API_KEY`** (Chutes inference token) plus `OPENAI_BASE_URL` / `OPENAI_MODEL` — do not reuse the Gemini key for Chutes.

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

Template or catalog changes need coordinated upgrades ([governance.md](governance.md)).

## Timeouts

| Variable | Meaning |
| -------- | ------- |
| `LEMMA_BLOCK_TIME_SEC_ESTIMATE` | Rough seconds per chain block; validators derive **forward HTTP wait** = blocks until the next problem-seed edge × this value (then clamped). |
| `LEMMA_FORWARD_WAIT_MIN_S` / `LEMMA_FORWARD_WAIT_MAX_S` | Floor and ceiling for that derived forward HTTP wait (validator client timeout per miner query). |
| `LEMMA_LLM_HTTP_TIMEOUT_S` | HTTP read timeout for one prover or judge completion — must fit within a round’s forward wait at typical chain heads. |
| `LEAN_VERIFY_TIMEOUT_S` | Sandbox `lake build` budget **per miner proof** (default 300 s). |

Validator **round cadence** is not configurable in Lemma: each validator waits for **subnet epoch boundaries** before running `run_epoch` — no wall-clock interval mode.

Timeout values are subnet policy: the operator publishes a single canonical `.env` (or equivalent) and every validator is expected to run that same configuration. Individual validators do not choose different budgets; drift breaks fairness and comparability ([governance.md](governance.md)). Forward HTTP wait follows **block height** (same edge as the next seed rotation), not a single operator-chosen wall-clock cap. If the operator’s published policy includes per-split multipliers (`LEMMA_TIMEOUT_SCALE_BY_SPLIT`, `LEMMA_TIMEOUT_SPLIT_*_MULT`), that is still one policy for the whole subnet, not a per-node setting.

## Miner deadlines vs validator processing (plain English)

**Miners** have an explicit **response** deadline: the synapse **`timeout`** / forward HTTP wait (derived from blocks until the next seed edge × `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, then clamped). If your axon does not complete the HTTP response in time, that round does not count as a successful candidate answer from you.

**Validators** do **not** get a matching global rule like “finish verifying and judging **every** successful miner before block *N* or before the next theorem.” Lemma picks **one** theorem when `run_epoch` **starts** and runs forward → verify → judge for that round; advancing blocks do **not** swap the theorem mid-batch or void in-flight grading. There is **no** separate “validator batch clock” in addition to the per-proof limits below. You still want fast hardware and tuning so each epoch completes in reasonable wall-clock time and stays competitive with other validators.

**What happens if one proof hits `LEAN_VERIFY_TIMEOUT_S`?** That miner’s Lean step **fails** (verify reason `timeout`). They are **not** verified for the round, so they get **no** judge score and **no** Pareto weight from that proof. Other miners in the same round are unaffected.

**What happens if the judge times out or errors?** That UID is **skipped** for scoring for the round (failure is logged; `judge_errors` in the epoch summary). Other judged miners are still scored.

Concurrency caps (`LEMMA_LEAN_VERIFY_MAX_CONCURRENT`, `LEMMA_JUDGE_MAX_CONCURRENT`) limit how many proofs are processed at once; extra work **queues**, it is not dropped because the chain moved.

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

Within one validator, a round finishes before the code waits for the **next subnet epoch boundary**.

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
- `JUDGE_PROVIDER=chutes` means the subnet judge on Chutes (OpenAI-compatible HTTP to `https://llm.chutes.ai/v1`; legacy `JUDGE_PROVIDER=openai` still works for the same client). **Validators** must use `OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2-TEE` and that base URL (enforced at startup). **Miners** may use any prover model via `PROVER_*` / `PROVER_MODEL`.
- Align with `uv run lemma meta` and optional `JUDGE_PROFILE_SHA256_EXPECTED`.

## Miner provenance

Optional `model_card` on the synapse labels the prover stack for exports.

## Validator isolation

Each validator queries miners independently; proofs are not merged across miners.

## Observability

Logs: `lemma_epoch_summary`; optional JSONL. No built-in dashboard ([production.md](production.md)).

## CI templates

[`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py) runs `lake build` on templates.

## Testnet checklist

1. `uv sync`; `.env` with test endpoint, `NETUID`, wallets.
2. Register (`btcli`).
3. Miner: reachable axon; prover keys.
4. Validator: Lean image; `uv run lemma meta`; smoke-test judge on files with `lemma judge --trace …`; full rehearsal without weights: `lemma validator dry-run` (FakeJudge by default; `LEMMA_DRY_RUN_REAL_JUDGE=1` for live judge); `LEMMA_FAKE_JUDGE=1` only for fully local stubs.
5. Confirm `set_weights` when ready.

## Throughput

One sampled problem per validator round. The forward HTTP wait (block-derived) bounds one miner response; the next round starts after the **next subnet epoch boundary**.

## `lemma --help` and Bittensor

`bittensor` loads lazily so top-level help stays normal Click output.

## Comparator / lean-eval

Core: `lake build` + axiom allowlist + cheat scan. Optional: [comparator.md](comparator.md); stricter isolation may follow [lean-eval](https://github.com/leanprover/lean-eval).
