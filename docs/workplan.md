# Lemma Core Workplan

This is the single active tracker for audit findings, current blockers, testing,
and next work. Keep decision records and threat-model docs as evidence, but do
not let parallel checklists drift.

## Current Baseline

- Repository: `spacetime-tao/lemma`, local checkout `/Users/leehall/lemma`.
- Current head during this audit:
  `b7088f00295fe0e23ad4a856ac43799b9acd8882`
  (`Remove stale judge config from proof-only path`).
- Live reward direction: proof passes Lean and can enter scoring, or proof
  fails Lean and does not enter scoring.
- Friendly operator UX belongs in `spacetime-tao/lemma-cli`; core Lemma owns
  protocol, problem selection, Lean verification, validator scoring, minimal
  service entrypoints, and consensus tests.

## What Is Good

- The live miner payload is centered on `proof_script`; informal reasoning is
  not reward-critical protocol data.
- Validators mechanically verify submitted proofs with the pinned Lean sandbox
  before scoring.
- Identical verified proofs are no longer dropped from live rewards; same-coldkey
  partitioning limits one-coldkey multi-hotkey multiplication after weights are
  computed.
- The generated problem registry has 40 builders and a metadata gate covering
  registry reachability/coherence.
- CLI bloat has been mostly moved to `lemma-cli`; core keeps minimal commands
  and redirects.
- Local baseline checks passed after the Hatch metadata fix:
  - `uv sync --extra dev`;
  - `uv run ruff check lemma tests tools`;
  - `uv run pytest tests/ -q --ignore=tests/test_docker_golden.py`
    (`255 passed, 1 skipped, 12 warnings`);
  - generated-template metadata gate for 40 builders;
  - Docker golden Lean verify (`1 passed in 210.60s`);
  - runtime Docker build smoke (`lemma-runtime:ci-smoke`).

## Current Blockers And Gaps

1. **GitHub re-check pending.**
   `b7088f0` failed before tests because Hatch rejected the `cli` optional
   dependency direct reference to `lemma-cli`. This working tree adds
   `tool.hatch.metadata.allow-direct-references = true`, and local
   `uv sync --extra dev` plus `docker build -f Dockerfile -t
   lemma-runtime:ci-smoke .` now pass. GitHub Actions still need to be checked
   after the fix lands.

2. **Tracker drift.**
   `AGENT_STATE.md`, `docs/workplan.md`, `docs/audit-remediation.md`, and
   `docs/incentive-roadmap.md` all contained overlapping status. This file is
   now the active tracker; `AGENT_STATE.md` is only the short chat-freeze
   handoff.

3. **Typing quality gap.**
   `uv run mypy lemma` currently reports `70 errors in 11 files`. This is not a
   CI blocker today, but it is a good hardening track after package/CI health is
   restored.

4. **Ops version drift.**
   Both known droplets are alive and services are active, but `/opt/lemma` is
   deployed at `82bba8d`, one commit behind `b7088f0`. Record only for this
   pass; do not deploy or restart services here.

5. **Real subnet evidence still matters.**
   Local proof PASS is necessary but not enough. The subnet still needs measured
   miner response time, prover latency, validator Lean verification time, scored
   miner count, timeout/fail reasons, set-weights behavior, and emission changes
   from live runs.

## Testing Matrix

Run these before claiming the repo is locally healthy:

```bash
uv sync --extra dev
uv run ruff check lemma tests tools
uv run pytest tests/ -q --ignore=tests/test_docker_golden.py
uv run python scripts/ci_verify_generated_templates.py
RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest \
  uv run pytest tests/test_docker_golden.py -v --tb=short
docker build -f Dockerfile -t lemma-runtime:ci-smoke .
```

Optional quality frontier:

```bash
uv run mypy lemma
```

Do not treat `mypy` as passing until its existing errors are fixed. Do not treat
GitHub as fixed until the latest Actions runs for `main` are checked directly.

## VPS Status

Current record-only state from the 2026-05-11 audit:

| Host | IP | Deployed commit | Running Lemma services |
| --- | --- | --- | --- |
| `lemma-lean-worker-1` | `167.99.145.132` | `82bba8d` | `lemma-lean-worker-http.service`, `lemma-validator.service` |
| `lemma-miner-1` | `161.35.50.115` | `82bba8d` | `lemma-miner.service`, `lemma-miner3.service`, `lemma-miner4.service`, `lemma-miner5.service`, `lemma-miner6.service`, `lemma-miner7.service` |

Next VPS testing should measure behavior, not add mechanism code:

- miner forward response time per UID/model;
- prover API latency and retry/timeout reasons;
- validator Lean verify time, cold and warm;
- remote worker versus local Docker worker reliability;
- set-weights, commit-reveal delay, and emission movement after reveal.

## Next Work Order

1. Land the Hatch direct-reference metadata fix and re-check GitHub Actions.
2. Keep this file as the only active audit/work tracker; leave
   `docs/audit-remediation.md` and `docs/incentive-roadmap.md` as pointer stubs.
3. Keep local checks and Docker runtime build smoke green before pushing.
4. Re-check GitHub Actions after the fix lands.
5. Only after CI/package health is restored, choose the next work slice:
   - typing hardening for the `mypy` errors;
   - VPS timing/observability run;
   - measured Lean worker throughput;
   - sybil/Pareto replay on real private exports.

## Non-Goals

- Do not redesign the live reward mechanism in this pass.
- Do not add proof-efficiency or prose/judge scoring to the live path.
- Do not deploy, restart, or mutate droplet services in this pass.
- Do not move validator scoring or consensus policy into `lemma-cli`.
- Do not add more defensive layers where a simpler data model can remove the
  invalid state.
