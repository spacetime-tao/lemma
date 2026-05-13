# Lemma Core Workplan

This is the single active tracker for audit findings, current blockers, testing,
and next work. Keep decision records and threat-model docs as evidence, but do
not let parallel checklists drift.

## Current Baseline

- Repository: `spacetime-tao/lemma`, local checkout `LOCAL_WORKSPACE/lemma`.
- Current local hardening batch: 2026-05-13 audit remediation, starting from
  `9546095` (`Track live ops hardening backlog`).
- Current deployed/GitHub-confirmed audit head:
  `8067b70` (`Harden set_weights result handling`), with `CI` and
  `Build and Push Docker Image` passing on GitHub Actions.
- Live reward direction: proof passes Lean and can enter scoring, or proof
  fails Lean and does not enter scoring.
- Operator UX belongs in the core `lemma` command; consensus policy stays in
  protocol, problem selection, Lean verification, validator scoring, and tests.
- Current audit docs:
  - [`cursor-audit.md`](cursor-audit.md): Cursor-assisted rating `7.5 / 10`.
  - [`codex-audit.md`](codex-audit.md): refreshed Codex rating `8.4 / 10`.

## What Is Good

- The live miner payload is centered on `proof_script`; informal reasoning is
  not reward-critical protocol data.
- Validators mechanically verify submitted proofs with the pinned Lean sandbox
  before scoring.
- Identical verified proofs are no longer dropped from live rewards; same-coldkey
  partitioning limits one-coldkey multi-hotkey multiplication after weights are
  computed.
- Default problem supply is hybrid: generated templates plus a curated catalog
  lane with authored dashboard statements. The generated registry has 80
  builders with explicit 10% / 35% / 55% easy / medium / hard split weights,
  template-owned topics, and a metadata/witness gate covering registry
  reachability/coherence.
- Normal operator workflows are consolidated under `lemma`: setup, doctor,
  status, problem views, preview, miner, and validator entrypoints.
- Validator hot-path side effects are bounded: export writes are non-fatal after
  scoring, disk preflight happens before miner queries, and verifier-local
  failures are accounted separately from proof failures.
- Lean workspace cache is bounded by both slot count and total bytes.
- Public dashboard refreshes are serialized with `flock` and remain outside the
  validator scoring path.
- Testnet Droplets are currently deployed at `8067b70`. First post-deploy round
  observed `verified=3`, `scored=3`, `verify_infra_errors=0`, no reject
  counters, and `set_weights success=True`.
- Local baseline checks after the 2026-05-13 hardening pass:
  - `.venv/bin/ruff check lemma tests tools`: passed;
  - `.venv/bin/mypy lemma`: passed
    (`Success: no issues found in 70 source files`);
  - `.venv/bin/pytest tests -q`: passed
    (`310 passed, 2 skipped, 12 warnings`);
  - `.venv/bin/python scripts/ci_verify_generated_templates.py`: passed
    (`OK: generated template metadata/witness gate covered 80 builders`);
  - `RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/pytest tests/test_docker_golden.py -v --tb=short`:
    passed (`1 passed in 208.57s`);
  - `RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/python scripts/ci_verify_generated_templates.py`:
    passed; all 80 generated template stubs and witnesses built in one Docker
    workspace;
  - `docker build -f Dockerfile -t lemma-runtime:ci-smoke .`: passed;
  - `.venv/bin/bandit -q -r lemma -ll`: passed with no medium/high findings;
  - `.venv/bin/bandit -q -r lemma`: 20 low-severity findings only;
  - `.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969`:
    passed (`No known vulnerabilities found, 3 ignored`).

## Recently Closed

- Validator inbound proof-size boundary: validator epochs reject oversized
  `resp.proof_script` payloads with `SYNAPSE_MAX_PROOF_CHARS` before scheduling
  Lean verification.
- Remote Lean worker safe default: unauthenticated non-loopback
  `lemma lean-worker` binds fail unless the explicit dev-only override is set.
- Binary proof eligibility docs: high-traffic docs separate the binary Lean
  eligibility gate from downstream allocation policy.
- Generated problem supply hardening: registry now has 80 builders and the
  local metadata/witness gate covers all of them.
- Hybrid supply design: default source is generated + curated catalog with
  deterministic 60 / 40 lane weights, authored `informal_statement` metadata,
  and `problem_supply_registry_sha256` for validator pinning.
- Export/write failure boundary: training JSONL append `OSError` no longer
  aborts `set_weights` after scoring is computed.
- Disk preflight: `LEMMA_VALIDATOR_MIN_FREE_BYTES` skips epochs before miner
  queries when root/cache free space is too low.
- Cache byte cap: `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES` prunes warm workspace
  slots by total size while protecting the active slot.
- Infra-error accounting: `timeout`, `oom`, `docker_error`, and `remote_error`
  are logged/exported as validator infrastructure failures and excluded from
  verify-credibility downgrades.
- All-fail proof epochs persist verify-credibility downgrades for ordinary Lean
  proof failures instead of losing them when nobody scored.
- RPC 429 backoff: validator cadence errors are caught inside the service loop,
  and rate-limit messages back off longer.
- Set-weights result handling: tuple-style false returns and raised RPC
  exceptions are failures, are retried, and produce a concrete final log message
  instead of `message=None`.
- Testnet deploy/evidence slice: validator/miner hosts were fast-forwarded from
  `d42addb` to `8067b70`; services restarted; first post-deploy round set
  weights successfully.
- Dashboard refresh isolation: the deploy script uses `flock`, cleans temp files,
  and keeps site git failures separate from validator scoring.
- Legacy live-adjacent aliases: `reasoning_only`,
  `LEMMA_JUDGE_PROFILE_ATTEST_*`, `JUDGE_PROFILE_SHA256_EXPECTED`, and
  `/lemma/judge_profile_sha256` are retired.

## Current Blockers And Gaps

1. **Separate Lean cache from the root filesystem in production.**
   The code now has preflight and byte pruning, but production validator/worker
   hosts should still mount `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` on its own
   volume or partition.

2. **Live alerting.**
   Add operator alerts for root/cache disk >80%, failed Lemma systemd units,
   repeated `epoch failed`, missing `lemma_epoch_summary` for N minutes, and
   repeated empty-score / skipped-weight epochs.

3. **Full Bandit low-severity cleanup.**
   CI's medium/high Bandit gate passes. Full Bandit still reports 20 low
   findings: intentional Lean/Docker subprocess calls and deterministic
   non-crypto RNG/jitter. Fix only when the change removes ambiguity or code.

4. **Live subnet/VPS evidence still matters.**
   Local and GitHub CI proof PASS are necessary but not enough. The subnet still
   needs measured miner response time, prover latency, validator Lean
   verification time over repeated rounds, timeout/fail reasons, set-weights
   behavior across RPC failures, and emission changes after reveal.

5. **External audit.**
   Before high-value mainnet operation, get independent review of validator
   infrastructure, Docker/remote worker exposure, Bittensor operations, and key
   custody.

## Next Work Order

1. Watch several more deployed rounds and record set-weights/emission movement,
   especially across any RPC retry event.
2. Add production alerts and a compact live health command/report covering
   commit, services, disk, cache slots, dashboard timer, latest epoch summary,
   and latest `set_weights`.
3. Plan a separate Lean cache volume or partition for validator/worker hosts.
4. Continue deleting or isolating optional research surfaces only when they
   touch live defaults or public operator UX.

## Testing Matrix

Run these before claiming the repo is locally healthy:

```bash
.venv/bin/ruff check lemma tests tools
.venv/bin/mypy lemma
.venv/bin/pytest tests -q
.venv/bin/python scripts/ci_verify_generated_templates.py
.venv/bin/bandit -q -r lemma -ll
.venv/bin/bandit -q -r lemma
.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969
RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest \
  .venv/bin/pytest tests/test_docker_golden.py -v --tb=short
RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest \
  .venv/bin/python scripts/ci_verify_generated_templates.py
docker build -f Dockerfile -t lemma-runtime:ci-smoke .
```

Docker-backed checks require a running Docker daemon and the Lean sandbox image.
Do not treat GitHub Actions as fixed-current unless the latest Actions runs for
the exact head are checked directly.

## VPS Status

No VPS check was performed during the 2026-05-13 local hardening pass. Treat
older droplet snapshots as stale until refreshed from live hosts.

| Host | IP | Deployed commit | Running Lemma services |
| --- | --- | --- | --- |
| `lemma-lean-worker-1` | `<validator-host>` | stale snapshot `82bba8d` | `lemma-lean-worker-http.service`, `lemma-validator.service` |
| `lemma-miner-1` | `<miner-host>` | stale snapshot `82bba8d` | `lemma-miner.service`, `lemma-miner3.service`, `lemma-miner4.service`, `lemma-miner5.service`, `lemma-miner6.service`, `lemma-miner7.service` |

Next VPS testing should measure behavior, not add mechanism code:

- miner forward response time per UID/model;
- prover API latency and retry/timeout reasons;
- validator Lean verify time, cold and warm;
- remote worker versus local Docker worker reliability;
- set-weights, commit-reveal delay, and emission movement after reveal.

## Non-Goals

- Do not redesign the live reward mechanism in this pass.
- Do not add proof-efficiency or prose/judge scoring to the live path.
- Do not deploy, restart, or mutate droplet services without an explicit live
  ops request.
- Do not move validator scoring or consensus policy into command glue.
- Do not add more defensive layers where a simpler data model can remove the
  invalid state.
