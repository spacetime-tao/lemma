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

Use `LOCAL_WORKSPACE/lemma` as the working checkout. It is clean and already at commit `6d8a441`.

Do not keep editing the temporary Codex snapshot. It was useful for inspection only.

### 2. Core Safety Fixes

These stay in `spacetime-tao/lemma` because they affect scoring agreement.

1. Fail closed when response body hash is missing or mismatched in production.
2. Reject missing `deadline_block` on responses that were sent with a deadline.
3. Make generated registry hashes cover the real template body and RNG version tag, not only names/order.
4. Fix generated problem documentation so the builder count matches code.
5. Expand the validator scoring/profile pin to cover subnet-critical settings beyond the judge prompt/model.
6. Make FakeJudge impossible in live validator mode unless an explicit local-only flag is active.

### 3. Scoring Simplification

These stay in the core repo, but should be handled as product decisions, not tiny patches.

1. Replace or reduce `proof_intrinsic_score`; length is a weak proxy for mathematical value.
2. Decide whether judged informal reasoning is part of the permanent incentive mechanism or a bootstrap aid.
3. Keep Lean pass/fail as the objective floor.
4. Avoid adding more scoring layers until the primary objective is one sentence.

### 4. Experimental Protocol Hooks

These should be either hardened or removed from the default mental model.

1. Miner verify attest: keep full validator Lean verify as default; do not let attest-only paths inflate credibility.
2. Commit-reveal: either add bounded cache/validator identity/clear threat model or leave it off and stop expanding it.
3. Judge peer attest: treat as operator coordination, not strong security.

### 5. CLI Extraction

This is the `lemma-cli` repo track.

Status: `spacetime-tao/lemma-cli` exists as a thin public wrapper. The first core trim moved the guided `start` surface out of the subnet repo. Later trims moved the `.env` setup/configure wizard, docs/glossary helpers, and local try-prover/rehearsal previews to `lemma-cli`, leaving redirect shims in core.

Move first:

1. Guided menu and start screen. **Done as a core trim; rebuild richer UX in `lemma-cli` only.**
2. Environment wizard. **Moved to `lemma-cli`; core has redirects only.**
3. Docs opener/glossary. **Moved to `lemma-cli`; core has redirects only.**
4. Shell activation helpers. **Removed from core; docs use standard `uv run` commands or explicit `.venv` activation.**
5. Local try-prover/rehearsal wrappers. **Moved to `lemma-cli`; core has redirects only.**
6. Human-friendly doctor/validator-check wrappers, once the core repo exposes stable machine-readable checks.

Keep temporarily in core:

1. Minimal `lemma validator start`.
2. Minimal `lemma miner start`.
3. Minimal `lemma verify`.
4. Minimal `lemma meta`.

The split is safe if `lemma-cli` depends on `lemma` as a Python package instead of copying consensus code.

### 6. Core Cleanup After CLI Split

Once `lemma-cli` exists and can call core functions:

1. Delete duplicate dry-run aliases. **Done: canonicalized to `miner dry-run`, `validator dry-run`, and `validator config`.**
2. Thin or remove no-op glue like `validator/query.py` and `validator/protocol_migration.py`. **Done: removed both; epoch calls `bt.Dendrite` directly.**
3. Move catalog-building helpers out of runtime package if only scripts/tests use them. **Done: builder/parser helpers moved to `tools/catalog`; runtime keeps `lemma/catalog/constants.py`.**
4. Remove root stubs and unused assets once docs no longer point at them. **Root cleanup done: removed `validator.py`, `voibes.jpeg`, obsolete `env.example`, superseded `scripts/load_minif2f.py`, and the old `scripts/lemma-run` wrapper. Comparator docs now match default-off behavior; `tiktoken` dependency removed by using a plain trace-length proxy. Larger misc items remain.**
5. Keep tests focused on proof acceptance, scoring, protocol integrity, and deterministic problem selection.

## First PR Sequence

1. Add this workplan and agree on repo split boundaries.
2. Patch generated problem count docs and registry hash contents.
3. Patch response integrity/deadline fail-closed behavior with tests.
4. Patch live validator FakeJudge fail-closed behavior.
5. Scaffold `lemma-cli` as a separate repo and move only non-consensus UI code first. **Started.**
6. Remove migrated CLI code from core after `lemma-cli` can install and run against it.

## Non-Goals For Now

- Do not redesign the entire subnet in one pass.
- Do not move validator scoring into the CLI repo.
- Do not add more config knobs to solve unclear incentives.
- Do not make commit-reveal or attest more central until their threat models are clean.
