# Lemma core workplan

This is the non-overlapping work map for making Lemma smaller, clearer, and safer.
The rule of thumb is: keep the subnet repository focused on consensus-critical behavior, and move operator convenience into a separate CLI package.

## Repositories

| Repo | Owns | Does not own |
| --- | --- | --- |
| `spacetime-tao/lemma` | Protocol, problem selection, Lean verification, validator scoring, miner/validator services, tests for consensus behavior. | Guided setup screens, shell activation helpers, docs openers, colored menus, broad onboarding UX. |
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
5. Expand the validator scoring/profile pin to cover subnet-critical settings beyond the judge prompt/model. **Done.**
6. Make FakeJudge impossible in live validator mode unless an explicit local-only flag is active. **Done.**
7. Document production Lean/toolchain image pinning so local `latest` stays a dev-only convenience. **Done:** [toolchain-image-policy.md](toolchain-image-policy.md).
8. Document the public deterministic problem-supply boundary and builder promotion checklist. **Done:** [problem-supply-policy.md](problem-supply-policy.md).
9. Expand the generated template registry with a small non-arithmetic batch. **Done:** 40 builders total; list, set, order, logic, and finite-set templates added.

### 3. Scoring Simplification

These stay in the core repo, but should be handled as product decisions, not tiny patches.

1. Replace or reduce `proof_intrinsic_score`; length is a weak proxy for mathematical value. **Default weight lowered to `0.10`; comment-only / blank-line padding normalized; compare-only Lean probe added; decision note, go/no-go gate, and collection runbook:** [proof-intrinsic-decision.md](proof-intrinsic-decision.md), [training_export.md](training_export.md). Next behavior change must choose to replace, keep low, or remove/reduce the heuristic from real export data plus padding fixtures, in a separate scoring commit.
2. Decide whether judged informal reasoning is part of the permanent incentive mechanism or a bootstrap aid. **Current stance documented:** [judge-incentive-decision.md](judge-incentive-decision.md) treats the judge as a bootstrap signal unless governance explicitly chooses it as a permanent product objective.
3. Keep Lean pass/fail as the objective floor. **Done:** [objective-decision.md](objective-decision.md) pins the current one-sentence objective as Lean-valid theorem proving, with judged reasoning documented as a bootstrap ranking layer.
4. Sybil/Pareto reward changes need evidence first. **Tooling ready:** private full exports now carry enough public challenge/coldkey context for `tools/sybil_replay_analyze.py` to compare dedup modes and K-miner clone pressure. **Still open:** collect real exports and choose a policy before changing live rewards.
5. Avoid adding more scoring layers until the primary objective is one sentence.

### 4. Experimental Protocol Hooks

These should be either hardened or removed from the default mental model.

1. Miner verify attest: keep full validator Lean verify as default; do not let attest-only paths inflate credibility. **Done for optional usable path: verify batch isolates per-UID verifier exceptions; attest-trusted responses must still match current challenge fields; v2 signatures bind validator hotkey; docs state this is not hardware remote attestation.**
2. Commit-reveal: keep active, with bounded cache, validator identity binding, shared commitment hex normalization, and an explicit same-round threat model. **Done for optional usable path; stronger public fairness would be a separate design.**
3. Judge peer attest: treat as operator coordination, not strong security. **Done: threat model documents all-of-N HTTP limits and skip as solo/dev only.**

### 5. CLI Extraction

This is the `lemma-cli` repo track.

Status: `spacetime-tao/lemma-cli` exists as a thin public wrapper. The first core trim moved the guided `start` surface out of the subnet repo. Later trims moved the `.env` setup/configure wizard, docs/glossary helpers, and local try-prover/rehearsal previews to `lemma-cli`, leaving redirect shims in core.

Move first:

1. Guided menu and start screen. **Done as a core trim; rebuild richer UX in `lemma-cli` only.**
2. Environment wizard. **Moved to `lemma-cli`; core has redirects only.**
3. Docs opener/glossary. **Moved to `lemma-cli`; core has redirects only.**
4. Shell activation helpers. **Removed from core; docs use standard `uv run` commands or explicit `.venv` activation.**
5. Local try-prover/rehearsal wrappers. **Moved to `lemma-cli`; core has redirects only.**
6. Human-friendly doctor/validator-check wrappers, once the core repo exposes stable machine-readable checks. **In progress:** `lemma-cli doctor` and `lemma-cli miner-observability` own the friendly views; moved-command redirects now share one small compatibility helper; core `validator-check` exits after READY / NOT READY and shares startup gates with `lemma validator start`; richer guided handoff belongs in `lemma-cli`.

Keep temporarily in core:

1. Minimal `lemma validator start`.
2. Minimal `lemma miner start`.
3. Minimal `lemma verify`.
4. Minimal `lemma meta`.

The split is safe if `lemma-cli` depends on `lemma` as a Python package instead of copying consensus code.

### 6. Core Cleanup After CLI Split

Once `lemma-cli` exists and can call core functions:

1. Delete duplicate dry-run aliases. **Done: canonicalized to `miner dry-run`, `validator dry-run`, and `validator config`.**
2. Thin or remove no-op glue like `validator/query.py` and `validator/protocol_migration.py`. **Done: removed both; epoch calls `bt.Dendrite` directly and no longer keeps a single-use UID helper.**
3. Move catalog-building helpers out of runtime package if only scripts/tests use them. **Done: builder/parser helpers moved to `tools/catalog`; runtime keeps `lemma/catalog/constants.py`.**
4. Remove root stubs and unused assets once docs no longer point at them. **Root cleanup done: removed `validator.py`, `voibes.jpeg`, obsolete `env.example`, superseded `scripts/load_minif2f.py`, and the old `scripts/lemma-run` wrapper. Comparator docs now match default-off behavior; `tiktoken` was removed, `anthropic` and `btcli` are optional, and the runtime Docker image no longer installs the full Docker engine. Larger misc items remain.**
5. Keep tests focused on proof acceptance, scoring, protocol integrity, and deterministic problem selection. **Ongoing: added coverage for optional multi-theorem seed mixing.**
6. Simplify small glue APIs when an audit item has a single unused path. **Started: removed the unused third return from `apply_ema_to_entries`; consolidated dedup best-by-key logic; removed unused scoring package re-exports; removed duplicate `ScoredEntry.composite`; added direct reward assembly coverage.**

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
