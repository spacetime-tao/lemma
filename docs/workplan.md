# Lemma Core Workplan

This is the single active tracker for audit findings, blockers, tests, and next
work.

Keep decision records as evidence. Do not let parallel checklists drift.

## Current Baseline

- Repo: `spacetime-tao/lemma`.
- Local checkout: `LOCAL_WORKSPACE/lemma`.
- Current `main`:
  `67dfd477c1a274e613b1ea5f01f80af24c2822ee`
  (`Fix Hatch direct refs and consolidate tracker docs`).
- GitHub CI run `25650611350` for `67dfd47`: passed.
- Live reward rule: proof passes Lean and can enter scoring, or proof fails Lean
  and cannot receive proof score.
- `lemma-cli` owns friendly operator UX. Core Lemma owns protocol, problem
  selection, Lean verification, validator scoring, service entrypoints, and
  consensus tests.

## What Is Good

- Miner payload centers on `proof_script`.
- Informal reasoning is not live reward data.
- Validators check proofs with the pinned Lean sandbox before scoring.
- Identical verified proofs are no longer dropped from live rewards.
- Same-coldkey partitioning limits one coldkey from multiplying rewards through
  many hotkeys.
- Generated problem registry has 40 builders and a metadata gate.
- CLI bloat mostly moved to `lemma-cli`.
- Hatch direct-reference metadata is fixed on `main`.
- Local checks and GitHub CI pass for the package/CI fix.

## Current Gaps

1. **Typing.** `uv run mypy lemma` reports `70 errors in 11 files`. This is not
   a CI blocker today, but it is a clear hardening track.
2. **Ops drift.** Both known droplets were alive and services were active, but
   `/opt/lemma` was deployed at `82bba8d`, behind current `main`. Record only
   unless the user asks for deploy/restart.
3. **Live subnet evidence.** Local PASS is not enough. We still need measured
   miner response time, prover latency, Lean verify time, scored miner count,
   timeout reasons, `set_weights` behavior, and emission movement.
4. **Docs readability.** This pass rewrites Markdown in plain language. Keep the
   same style in future docs.

## Testing Matrix

Run these before claiming local health:

```bash
uv sync --extra dev
uv run ruff check lemma tests tools
uv run pytest tests/ -q --ignore=tests/test_docker_golden.py
uv run python scripts/ci_verify_generated_templates.py
RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest \
  uv run pytest tests/test_docker_golden.py -v --tb=short
docker build -f Dockerfile -t lemma-runtime:ci-smoke .
```

Optional quality check:

```bash
uv run mypy lemma
```

Do not call `mypy` passing until the existing errors are fixed.

## VPS Status

Last checked during the 2026-05-11 audit:

| Host | IP | Deployed commit | Running Lemma services |
| --- | --- | --- | --- |
| `lemma-lean-worker-1` | `<validator-host>` | `82bba8d` | `lemma-lean-worker-http.service`, `lemma-validator.service` |
| `lemma-miner-1` | `<miner-host>` | `82bba8d` | `lemma-miner.service`, `lemma-miner3.service`, `lemma-miner4.service`, `lemma-miner5.service`, `lemma-miner6.service`, `lemma-miner7.service` |

Next VPS testing should measure behavior:

- miner response time by UID/model;
- prover API latency and retry reasons;
- validator Lean time, cold and warm;
- remote worker versus local Docker worker reliability;
- `set_weights`, commit-reveal delay, and emission movement.

## Next Work Order

1. Finish and verify the plain-language Markdown pass.
2. Keep this file as the only active work tracker.
3. Keep `local handoff note` as the short chat-freeze handoff.
4. Choose one next slice:
   - fix `mypy` errors;
   - run VPS timing and observability tests;
   - measure Lean worker throughput;
   - run Sybil/Pareto replay on real private exports.

## Non-Goals

- Do not redesign live rewards in this pass.
- Do not add proof-efficiency or prose/judge scoring to the live path.
- Do not deploy, restart, or mutate droplet services in this pass.
- Do not move validator scoring into `lemma-cli`.
- Do not add defensive layers when simpler data flow can remove the invalid
  state.
