# Lemma Core Workplan

This is the single active tracker for audit findings, current blockers, testing,
and next work. Keep decision records and threat-model docs as evidence, but do
not let parallel checklists drift.

## Current Baseline

- Repository: `spacetime-tao/lemma`, local checkout `LOCAL_WORKSPACE/lemma`.
- Last CI-verified audit-fix head:
  `00e18051933b76b3d097956b79adeec236088711`
  (`Clarify proof eligibility versus allocation`).
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
- The generated problem registry has 72 builders with explicit 10% / 35% /
  55% easy / medium / hard split weights, template-owned topics, and a
  metadata/witness gate covering registry reachability/coherence.
- Normal operator workflows are consolidated under `lemma`: setup, doctor,
  status, problem views, preview, miner, and validator entrypoints.
- Local baseline checks after generated supply hardening:
  - `.venv/bin/ruff check .`;
  - `.venv/bin/mypy lemma`
    (`Success: no issues found in 69 source files`);
  - `.venv/bin/pytest -q`
    (`280 passed, 2 skipped, 12 warnings`);
  - `.venv/bin/python scripts/ci_verify_generated_templates.py`
    (`OK: generated template metadata/witness gate covered 72 builders`);
- Prior security hygiene checks from the remote worker safe-default pass:
  - `.venv/bin/bandit -q -r lemma -ll`;
  - `.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969`
    (`No known vulnerabilities found, 3 ignored`).
- Latest checked GitHub Actions CI run for `main` before this patch,
  [`25732798918`](https://github.com/spacetime-tao/lemma/actions/runs/25732798918),
  passed the `test` job on `5a9761d`; `docker-lean-sandbox` failed after the
  generated-template witness multiplex, then the old automatic bisection
  exhausted runner disk. The next CI run should preserve the real Lean output
  because generated-template bisection is now opt-in.
- Docker image publish passed on code commit `551b217`. The final `00e1805`
  commit was docs-only, so no image-publish run was needed for it.

## Recently Closed

- Validator inbound proof-size boundary: validator epochs now reject oversized
  `resp.proof_script` payloads with `SYNAPSE_MAX_PROOF_CHARS` before scheduling
  Lean verification.
- Remote Lean worker safe default: unauthenticated non-loopback `lemma
  lean-worker` binds now fail unless the explicit dev-only override is set.
- Binary proof eligibility docs: high-traffic docs now separate the binary Lean
  eligibility gate from downstream allocation policy.
- Generated problem supply hardening: registry expanded from 40 builders
  (10 easy, 22 medium, 8 hard) to 72 builders (10 easy, 30 medium, 32 hard);
  default split selection now targets 10% / 35% / 55% easy / medium / hard.
  Old registry SHA:
  `e7446626f8d05748fc72b7d8ad41f271d7e688e84d398be0b1d5f3f8974a4dbe`.
  New registry SHA:
  `4824b9dd028b5cd6af01ff9e32386e716b1c12c1ef96bd992efd69e7ba38e2d7`.
  Local cheap evidence passed:
  `.venv/bin/python scripts/ci_verify_generated_templates.py`
  (`OK: generated template metadata/witness gate covered 72 builders`).
  Docker witness-proof evidence still requires a Docker-capable CI/host.

## Current Blockers And Gaps

1. **Full Bandit low-severity cleanup.**
   CI's medium/high Bandit gate passes. A full Bandit run still reports
   low-severity subprocess, seeded RNG, `assert`, and cleanup-exception items.
   Only fix these when the change removes ambiguity or code.

2. **Live subnet/VPS evidence still matters.**
   Local and GitHub CI proof PASS are necessary but not enough. The subnet still
   needs measured miner response time, prover latency, validator Lean
   verification time, scored miner count, timeout/fail reasons, set-weights
   behavior, and emission changes from live runs.

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

1. Choose the next live evidence slice:
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
