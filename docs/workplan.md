# Lemma Core Workplan

This is the single active tracker for audit findings, current blockers, testing,
and next work. Keep decision records and threat-model docs as evidence, but do
not let parallel checklists drift.

## Current Baseline

- Repository: `spacetime-tao/lemma`, local checkout `LOCAL_WORKSPACE/lemma`.
- Current head before the remote worker safe-default fix:
  `f06ab1ad1a94a9787c07ee39169f1e089fc2f939`
  (`Refresh audit next steps after proof cap`).
- That head had already been pushed to GitHub before this follow-up fix began.
- Live reward direction: proof passes Lean and can enter scoring, or proof
  fails Lean and does not enter scoring.
- Operator UX belongs in the core `lemma` command; consensus policy stays in
  protocol, problem selection, Lean verification, validator scoring, and tests.
- Current audit docs:
  - [`cursor-audit.md`](cursor-audit.md): Cursor-assisted rating `7.5 / 10`.
  - [`codex-audit.md`](codex-audit.md): Codex rating `7.2 / 10`.

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
- Normal operator workflows are consolidated under `lemma`: setup, doctor,
  status, problem views, preview, miner, and validator entrypoints.
- Local baseline checks after the remote worker safe-default fix:
  - `.venv/bin/ruff check lemma tests tools`;
  - `.venv/bin/mypy lemma`
    (`Success: no issues found in 69 source files`);
  - `.venv/bin/pytest tests -q`
    (`261 passed, 2 skipped, 12 warnings`);
  - generated-template metadata gate for 40 builders;
  - `.venv/bin/bandit -q -r lemma -ll`;
  - `.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969`
    (`No known vulnerabilities found, 3 ignored`).

## Recently Closed

- Validator inbound proof-size boundary: validator epochs now reject oversized
  `resp.proof_script` payloads with `SYNAPSE_MAX_PROOF_CHARS` before scheduling
  Lean verification.
- Remote Lean worker safe default: unauthenticated non-loopback `lemma
  lean-worker` binds now fail unless the explicit dev-only override is set.
- Binary proof eligibility docs: high-traffic docs now separate the binary Lean
  eligibility gate from downstream allocation policy.

## Current Blockers And Gaps

1. **Full Bandit low-severity cleanup.**
   CI's medium/high Bandit gate passes. A full Bandit run still reports
   low-severity subprocess, seeded RNG, `assert`, and cleanup-exception items.
   Only fix these when the change removes ambiguity or code.

2. **Real subnet evidence still matters.**
   Local proof PASS is necessary but not enough. The subnet still needs measured
   miner response time, prover latency, validator Lean verification time, scored
   miner count, timeout/fail reasons, set-weights behavior, and emission changes
   from live runs.

## Testing Matrix

Run these before claiming the repo is locally healthy:

```bash
.venv/bin/ruff check lemma tests tools
.venv/bin/mypy lemma
.venv/bin/pytest tests -q
.venv/bin/python scripts/ci_verify_generated_templates.py
.venv/bin/bandit -q -r lemma -ll
.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969
RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest \
  .venv/bin/pytest tests/test_docker_golden.py -v --tb=short
docker build -f Dockerfile -t lemma-runtime:ci-smoke .
```

Docker-backed checks require a running Docker daemon and the Lean sandbox image.
Do not treat GitHub Actions as fixed-current unless the latest Actions runs for
`main` are checked directly.

## VPS Status

No VPS check was performed during the Codex audit doc pass. The last recorded
state below may be stale and should be refreshed before any deployment claim:

| Host | IP | Deployed commit | Running Lemma services |
| --- | --- | --- | --- |
| `lemma-lean-worker-1` | `<validator-host>` | `82bba8d` | `lemma-lean-worker-http.service`, `lemma-validator.service` |
| `lemma-miner-1` | `<miner-host>` | `82bba8d` | `lemma-miner.service`, `lemma-miner3.service`, `lemma-miner4.service`, `lemma-miner5.service`, `lemma-miner6.service`, `lemma-miner7.service` |

Next VPS testing should measure behavior, not add mechanism code:

- miner forward response time per UID/model;
- prover API latency and retry/timeout reasons;
- validator Lean verify time, cold and warm;
- remote worker versus local Docker worker reliability;
- set-weights, commit-reveal delay, and emission movement after reveal.

## Next Work Order

1. Re-run Docker-backed Lean golden and runtime Docker build smoke when Docker
   is available.
2. Then choose the next evidence slice:
   - VPS timing/observability run;
   - measured Lean worker throughput;
   - sybil/reward replay on real private exports;
   - low-severity Bandit cleanup where it removes code or ambiguity.

## Non-Goals

- Do not redesign the live reward mechanism in this pass.
- Do not add proof-efficiency or prose/judge scoring to the live path.
- Do not deploy, restart, or mutate droplet services in this pass.
- Do not move validator scoring or consensus policy into command glue.
- Do not add more defensive layers where a simpler data model can remove the
  invalid state.
