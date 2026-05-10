# Lemma core workplan

This is the non-overlapping work map for making Lemma smaller, clearer, and safer.
The rule of thumb is: keep the subnet repository focused on consensus-critical behavior, and move operator convenience into a separate CLI package.

## Repositories

| Repo | Owns | Does not own |
| --- | --- | --- |
| `spacetime-tao/lemma` | Protocol, problem selection, Lean verification, validator scoring, minimal validator service, reference miner compatibility path, tests for consensus behavior. | Guided setup screens, shell activation helpers, docs openers, colored menus, broad onboarding UX, competitive miner strategy. |
| `spacetime-tao/lemma-cli` | Human-friendly setup, doctor checks, guided miner/validator flows, docs shortcuts, local rehearsal wrappers. | Scoring rules, Bittensor weight logic, Lean proof acceptance policy, generated problem registry. |

Splitting the CLI is possible, but it should be done in stages. The core repo currently exposes the `lemma` console command, and operators use it for both core actions and onboarding. A hard cut would break workflows; a staged cut keeps the subnet usable while the code gets leaner.

## Workstreams

### 1. Local Source Of Truth

Use `/Users/leehall/lemma` as the working checkout. It is clean and synced with `main`.

Do not keep editing the temporary Codex snapshot. It was useful for inspection only.

### 2. Core Safety Fixes

These stay in `spacetime-tao/lemma` because they affect scoring agreement.

1. Fail closed when response body hash is missing or mismatched in production. **Done.**
2. Reject missing `deadline_block` on responses that were sent with a deadline. **Done.**
3. Make generated registry hashes cover the real template body and RNG version tag, not only names/order. **Done.**
4. Fix generated problem documentation so the builder count matches code. **Done.**
5. Expand the validator scoring/profile pin to cover subnet-critical settings beyond optional prose-evaluator settings. **Done.**
6. Make FakeJudge impossible in live validator mode unless an explicit local-only flag is active. **Done.**
7. Document production Lean/toolchain image pinning so local `latest` stays a dev-only convenience. **Done:** [toolchain-image-policy.md](toolchain-image-policy.md).
8. Document the public deterministic problem-supply boundary and builder promotion checklist. **Done:** [problem-supply-policy.md](problem-supply-policy.md).
9. Expand the generated template registry with a small non-arithmetic batch. **Done:** 40 builders total; list, set, order, logic, and finite-set templates added.

### 3. Future Problem Supply

These are product and governance tracks, not v0 launch blockers.

1. Keep generated easy / medium / hard traffic as the launch lane. It gives the network steady work, predictable verification cost, and simple operator expectations.
2. Treat open-problem campaigns as a later campaign / bounty lane: reviewed Lean statements, faithfulness certificates, dependency graphs, and submit-when-ready proofs. **Tracked:** [open-problem-campaigns.md](open-problem-campaigns.md).
3. Do not put large open-problem libraries in this core repo during v0. A future `LemmaOpenProblems`-style repo can own campaign Lean files, registries, faithfulness docs, and roadmaps; core should add protocol support only when the lane is ready.

### 4. Scoring Simplification

These stay in the core repo, but should be handled as product decisions, not tiny patches.

1. Make the long-term reward path proof-only. **Decision recorded:** [proof-only-incentives.md](proof-only-incentives.md) defines the target as Lean-valid proof plus deterministic proof-efficiency signals; informal reasoning is optional metadata, not a reward axis.
2. Replace `proof_intrinsic_score`; length is a weak proxy for mathematical value and the current version rewards bulk. Use a conservative proof-efficiency scorer that prefers lower stripped proof cost and Lean-backed proof-shape metrics after Lean pass. Keep proof-metric runtime cost visible.
3. Keep Lean pass/fail as the objective floor. **Done:** [objective-decision.md](objective-decision.md) pins the objective as valid, efficient Lean proofs.
4. Sybil/Pareto reward changes need evidence first. **Tooling ready:** private full exports now carry enough public challenge/coldkey context for `tools/sybil_replay_analyze.py` to compare dedup modes and K-miner clone pressure, report concrete `decision_data_gaps`, and [sybil_economics.md](sybil_economics.md) now includes the policy rubric for interpreting that replay. **Still open:** collect real exports and choose a policy before changing live rewards.
5. Avoid adding more scoring layers until the primary objective is one sentence.

### 5. Experimental Protocol Hooks

These should be either hardened or removed from the default mental model.

1. Miner verify attest: keep full validator Lean verify as default; do not let attest-only paths inflate credibility. **Done for optional usable path: verify batch isolates per-UID verifier exceptions; attest-trusted responses must still match current challenge fields; v2 signatures bind validator hotkey; docs state this is not hardware remote attestation.**
2. Commit-reveal: keep active, with bounded cache, validator identity binding, shared commitment hex normalization, and an explicit same-round threat model. **Done for optional usable path; stronger public fairness would be a separate design.**
3. Validator profile peer attest: treat as operator coordination, not strong security. **Done: threat model documents all-of-N HTTP limits and skip as solo/dev only.**
4. Wire transport: keep current Dendrite/Axon path until a major-release HTTP + Epistula migration is explicitly chosen. **Bounded:** [transport.md](transport.md) now records the migration gate and decision template.
5. Reference miner: keep the bundled miner minimal and compatibility-focused while the shipping protocol remains Axon-based. **Bounded:** [miner.md](miner.md) records that richer miner UX belongs in `lemma-cli` and miner-artifact/container designs are separate protocol work.

### 5a. Validator Throughput And Cadence

This is the path toward shorter theorem windows without making validators fall
behind. Treat each item as a measured step, not a promise that 5-minute windows
are safe on every machine.

1. Reuse identical Lean verification payloads within an epoch. **Done:** one
   Lean check is copied to miners that submitted the exact same theorem/proof
   payload before proof-side scoring.
2. Avoid duplicate cold-cache warmups for the same template. **Done:** concurrent
   same-template proofs now singleflight through one cold warmup, then reuse the
   published warm workspace.
3. Measure a remote Lean worker pool on Linux hardware. **Next:** this should be
   the first real scaling path before trusting 5-minute cadence assumptions.
4. Revisit miner local-verify attest only after miners reliably run local Lean
   and validators keep a nonzero spot-check rate.
5. Consider 50-block (~10 minute) windows before 25-block (~5 minute) windows
   unless real validator timing data clears the smaller budget.

### 6. CLI Extraction

This is the `lemma-cli` repo track.

Status: `spacetime-tao/lemma-cli` exists as a thin public wrapper. The first core trim moved the guided `start` surface out of the subnet repo. Later trims moved the `.env` setup/configure wizard, docs/glossary helpers, local try-prover/rehearsal previews, theorem status/problem inspection, one-shot judge preview, and validator config summary to `lemma-cli`, leaving redirect shims in core. The remaining core `lemma meta` command now prints concise hashes by default and keeps full canonical JSON in `--raw`.

Move first:

1. Guided menu and start screen. **Done as a core trim; rebuild richer UX in `lemma-cli` only.**
2. Environment wizard. **Moved to `lemma-cli`; core has redirects only.**
3. Docs opener/glossary. **Moved to `lemma-cli`; core has redirects only.**
4. Shell activation helpers. **Removed from core; docs use standard `uv run` commands or explicit `.venv` activation.**
5. Local try-prover/rehearsal wrappers. **Moved to `lemma-cli`; core has redirects only.**
6. Theorem status/problem inspection. **Moved to `lemma-cli`; core has redirects only.**
7. One-shot judge preview on saved files. **Moved to `lemma-cli`; core has redirects only.**
8. Validator config summary. **Moved to `lemma-cli`; core has redirects only.**
9. Human-friendly doctor/validator-check wrappers, once the core repo exposes stable machine-readable checks. **In progress:** `lemma-cli doctor` and `lemma-cli miner-observability` own the friendly views; moved-command redirects now share one small compatibility helper; core `validator-check` exits after READY / NOT READY and shares startup gates with `lemma validator start`; richer guided handoff belongs in `lemma-cli`.

Keep temporarily in core:

1. Minimal `lemma validator start`.
2. Minimal `lemma miner start`.
3. Minimal `lemma verify`.
4. Minimal `lemma meta` (hashes by default; full JSON via `--raw`).
5. Reference miner internals required by the current Axon protocol path.

The split is safe if `lemma-cli` depends on `lemma` as a Python package instead of copying consensus code.

### 7. Core Cleanup After CLI Split

Once `lemma-cli` exists and can call core functions:

Current `wc -l` snapshot after cleanup: `lemma/` is **7 842** Python lines across **63** files, down from the Round 3 cited **12 630**. `lemma/cli/` is **885** lines across **4** files, down from **5 398** lines across **16** files. Tests/docs grew because the remediation work added safety coverage, analyzer guards, and decision records.

1. Delete duplicate dry-run aliases. **Done: canonicalized to `miner dry-run` and `validator dry-run`; validator config summary moved to `lemma-cli validator-config`.**
2. Thin or remove no-op glue like `validator/query.py` and `validator/protocol_migration.py`. **Done: removed both; epoch calls `bt.Dendrite` directly and no longer keeps a single-use UID helper.**
3. Move catalog-building helpers out of runtime package if only scripts/tests use them. **Done: builder/parser helpers moved to `tools/catalog`; runtime keeps `lemma/catalog/constants.py`.**
4. Remove root stubs and unused assets once docs no longer point at them. **Root cleanup done: removed `validator.py`, `voibes.jpeg`, obsolete `env.example`, superseded `scripts/load_minif2f.py`, the old `scripts/lemma-run` wrapper, stale local-loop example, and legacy burn validator demo. Comparator docs now match default-off behavior; `tiktoken` was removed, `anthropic` and `btcli` are optional, and the runtime Docker image no longer installs the full Docker engine. Larger misc items remain.**
5. Keep tests focused on proof acceptance, scoring, protocol integrity, and deterministic problem selection. **Ongoing:** added coverage for optional multi-theorem seed mixing; removed the low-value problem-view title-case test.
6. Simplify small glue APIs when an audit item has a single unused path. **Ongoing:** removed the unused third return from `apply_ema_to_entries`; consolidated dedup best-by-key logic; removed unused scoring package re-exports; removed duplicate `ScoredEntry.composite`; inlined trace-length scoring; inlined miner default priority; removed the single-use validator UID helper; inlined the single-use split-timeout multiplier and topic-label formatter; kept package imports light by removing unused re-exports; removed unused strict-judge and problem-seed label helpers; moved `.env` merge helper to `lemma-cli`; added direct reward assembly coverage.

## First PR Sequence

1. Add this workplan and agree on repo split boundaries. **Done.**
2. Patch generated problem count docs and registry hash contents. **Done.**
3. Patch response integrity/deadline fail-closed behavior with tests. **Done.**
4. Patch live validator FakeJudge fail-closed behavior. **Done.**
5. Scaffold `lemma-cli` as a separate repo and move only non-consensus UI code first. **Started.**
6. Remove migrated CLI code from core after `lemma-cli` can install and run against it. **Mostly done; keep minimal core commands.**

## Non-Goals For Now

- Do not redesign the entire subnet in one pass.
- Do not move validator scoring into the CLI repo.
- Do not add more config knobs to solve unclear incentives.
- Do not make commit-reveal or attest more central than their documented threat models justify.
