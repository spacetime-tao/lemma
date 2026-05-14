# Lemma Core Workplan

This is the single active tracker for audit findings, current blockers, testing,
and next work. Keep decision records and threat-model docs as evidence, but do
not let parallel checklists drift.

## Current Baseline

- Repository: `spacetime-tao/lemma`, local checkout `LOCAL_WORKSPACE/lemma`.
- Latest runtime-impacting batch covered by this tracker: `28fb364` (`Expand
  generated supply and trust docs`) after the 2026-05-14 generated-builder
  expansion and validator-only deploy.
- Latest GitHub-confirmed runtime head: `0ff1068` (`Record CI evidence for
  set_weights cleanup`), with `CI` passing on GitHub Actions run
  `25793725075`. The preceding code commit `d95411b` also had `CI` and
  `Build and Push Docker Image` passing on runs `25793209291` and
  `25793209296`. The newer `28fb364` head has local tests and Docker Lean
  template verification recorded below, but this tracker did not re-check
  GitHub Actions.
- Current testnet Droplet head: validator / Lean worker host checkout is
  `28fb364`; the validator service was restarted. The miner host remains
  `0ff1068`.
- Live reward direction: proof passes Lean and becomes reward-eligible, or
  proof fails Lean and cannot receive miner rewards.
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
  lane with authored dashboard statements. The local working registry has 100
  builders with explicit 10% / 35% / 50% / 5% easy / medium / hard / extreme
  split weights, template-owned topics, and a metadata/witness gate covering
  registry reachability/coherence.
- Normal operator workflows are consolidated under `lemma`: setup, doctor,
  status, problem views, preview, miner, and validator entrypoints.
- Validator hot-path side effects are bounded: export writes are non-fatal after
  scoring, disk preflight happens before miner queries, and verifier-local
  failures are accounted separately from proof failures.
- Lean workspace cache is bounded by both slot count and total bytes.
- Public dashboard refreshes are serialized with `flock` and remain outside the
  validator scoring path.
- Testnet Droplets reached `0ff1068` on 2026-05-13. The earlier `8067b70`
  deploy observed `verified=3`, `scored=3`, `verify_infra_errors=0`, no reject
  counters, and `set_weights success=True`. The first observed `0ff1068` round
  at `2026-05-13 10:59 UTC` verified/scored 5 proofs with
  `verify_infra_errors=0`; `set_weights` returned false, and the deployed
  cleanup logged `success=False without message`. A follow-up `0ff1068`
  extreme-split round at `2026-05-13 11:10 UTC` verified/scored 2 proofs with
  `verify_infra_errors=0` and `set_weights success=True`. The 2026-05-14
  generated-supply rollout moved the validator / Lean worker host checkout to
  `28fb364`, refreshed pins, restarted `lemma-validator`, and logged
  `problem_supply_registry_sha256=8b7dccd4fc2a1cf68ad1e1e0ee35ea8680bdc05b24abdb7819ec1dbaee0c1556`
  with `problem_source=hybrid`. The first observed post-`28fb364` round at
  `2026-05-14 05:46 UTC` verified/scored 3 proofs with
  `verify_infra_errors=0` and `set_weights success=True`.
- Read-only droplet sampling later on 2026-05-13 found continued verified/scored
  rounds, active dashboard publishing, and intermittent false/no-message
  `set_weights` results from the deployed code. The latest sampled round at
  `2026-05-13 10:04 UTC` had `verified=4`, `scored=4`,
  `verify_infra_errors=0`, and `set_weights success=True`.
- Local baseline checks after the generated-builder expansion:
  - `.venv/bin/ruff check lemma tests tools`: passed;
  - `.venv/bin/mypy lemma`: passed
    (`Success: no issues found in 70 source files`);
  - `.venv/bin/pytest tests -q`: passed
    (`315 passed, 2 skipped, 12 warnings`);
  - `.venv/bin/python scripts/ci_verify_generated_templates.py`: passed
    (`OK: generated template metadata/witness gate covered 100 builders`);
  - local generated registry hash:
    `b926194367c2b0ef25dd5da4179256e7b70185cf3eb0543cbc603a73a45efff3`;
  - local hybrid problem-supply hash:
    `8b7dccd4fc2a1cf68ad1e1e0ee35ea8680bdc05b24abdb7819ec1dbaee0c1556`;
  - `RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/python scripts/ci_verify_generated_templates.py`:
    passed; all 100 generated template stubs and witnesses built in one Docker
    workspace;
  - `git diff --check`: passed.

## Recently Closed

- Validator inbound proof-size boundary: validator epochs reject oversized
  `resp.proof_script` payloads with `SYNAPSE_MAX_PROOF_CHARS` before scheduling
  Lean verification.
- Remote Lean worker safe default: unauthenticated non-loopback
  `lemma lean-worker` binds fail unless the explicit dev-only override is set.
- Binary proof eligibility docs: high-traffic docs separate the binary Lean
  eligibility gate from downstream allocation policy.
- Generated problem supply expansion: local working registry now has 100
  builders across easy / medium / hard / extreme splits, including first-batch
  templates for midpoint geometry, finite averages, difference quotients,
  finite constant sums, graph adjacency, Diophantine witnesses, and stronger
  inequalities.
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
- No-message set-weights false returns: the deployed follow-up normalizes tuple,
  dict, and object false/no-message returns to `success=False without message`
  instead of logging `(False, None)`. Live logs on `0ff1068` confirmed this at
  `2026-05-13 10:59 UTC`.
- Current-head droplet deploy: validator/miner hosts were fast-forwarded from
  `8067b70` to `0ff1068`; old subnet pins failed closed; pins were refreshed to
  profile
  `85155229a2c1a0dd9537434d89a7c924368f888e4602b6d909757b09285b0a9c` and
  problem-supply
  `f4ae425ad437c97b00d47b7ba97f97e1ff4cec8d5d66290c8b2364d91f822311`; services
  are active.
- Generated-supply validator deploy: validator / Lean worker host checkout was
  fast-forwarded to `28fb364`; `lemma-validator` was restarted with profile pin
  `85155229a2c1a0dd9537434d89a7c924368f888e4602b6d909757b09285b0a9c` and
  problem-supply pin
  `8b7dccd4fc2a1cf68ad1e1e0ee35ea8680bdc05b24abdb7819ec1dbaee0c1556`.
  An initial pin refresh from the wrong working directory failed closed on
  startup; rerunning from `/opt/lemma` corrected the pins and the service came
  up active.
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

2. **Watch continued `28fb364` validator rounds.**
   The first observed `28fb364` round verified/scored 3 proofs and set weights
   successfully. Continued monitoring should record reveal/emission movement
   and any repeated RPC false returns.

3. **Live alerting.**
   Add operator alerts for root/cache disk >80%, failed Lemma systemd units,
   repeated `epoch failed`, missing `lemma_epoch_summary` for N minutes, and
   repeated empty-score / skipped-weight epochs.

4. **Full Bandit low-severity cleanup.**
   CI's medium/high Bandit gate passes. Full Bandit still reports 20 low
   findings: intentional Lean/Docker subprocess calls and deterministic
   non-crypto RNG/jitter. Fix only when the change removes ambiguity or code.

5. **Problem supply expansion roadmap.**
   Open-problem campaign design now lives in
   [`open-problem-campaigns.md`](open-problem-campaigns.md). Normal cadence
   expansion should start with generated builders for missing topics, then
   promote reviewed solved contest rows, and only later add campaign/bounty
   protocol support for locked open-problem targets.

6. **Source/license hygiene.**
   The live generated and curated problem supply is repo-authored and
   witness-backed. Before any external miniF2F, Compfiles, PutnamBench,
   FormalMATH, mathlib, or Formal Conjectures material enters live `hybrid` or
   a campaign registry, record source, revision, license, attribution, split
   role, and witness-proof status. Also add a tracked top-level Apache-2.0
   `LICENSE` file, since the repo currently declares Apache-2.0 in `README.md`
   and `pyproject.toml`.

7. **Live subnet/VPS evidence still matters.**
   Local and GitHub CI proof PASS are necessary but not enough. The subnet still
   needs measured miner response time, prover latency, validator Lean
   verification time over repeated rounds, timeout/fail reasons, set-weights
   behavior across RPC failures, and emission changes after reveal.

8. **Trust-minimized release evidence.**
   The live path should be described as trust-minimized, not absolutely
   trustless. Next release work should publish Git tag/commit, immutable sandbox
   image ref or digest, Lean toolchain, Mathlib revision,
   `validator_profile_sha256`, `problem_supply_registry_sha256`,
   `generated_registry_sha256`, Docker witness-gate evidence, cutover window,
   and rollback pins.

9. **Public verification logs.**
   Design the smallest public evidence format that lets a third party rerun a
   round: theorem id, theorem statement, proof or proof digest,
   registry/profile hashes, sandbox image ref, verification result, and relevant
   timing/failure reason. Do not add protocol machinery until the format is
   clear.

10. **Open-problem faithfulness review.**
    Formal Conjectures-style work remains a candidate-source lane until the
    reviewed statement, source citation, reviewer sign-off, statement hash, and
    caveats are recorded in the campaign registry.

11. **External audit.**
   Before high-value mainnet operation, get independent review of validator
   infrastructure, Docker/remote worker exposure, Bittensor operations, and key
   custody.

## Next Work Order

1. Watch continued `28fb364` validator rounds and record reveal/emission
   movement, especially across any RPC retry event.
2. Add a compact live health command/report covering commit, services, disk,
   cache slots, dashboard timer, latest epoch summary, and latest
   `set_weights`.
3. Add production alerts using the same live health signals.
4. Add release-evidence output or docs that bundle commit, image digest,
   validator profile hash, problem-supply hash, generated-registry hash, and
   cutover/rollback pins.
5. Plan public verification logs for rerunning completed rounds.
6. Plan a separate Lean cache volume or partition for validator/worker hosts.
7. Add the next generated-builder expansion batch for remaining missing topics
   named in [`problem-supply-policy.md`](problem-supply-policy.md).
8. Promote solved contest-style curated rows only after source/license review
   and witness-proof verification.
9. Keep campaign/bounty protocol machinery out of the live path until a locked
   open-problem target requires it.
10. Continue deleting or isolating optional research surfaces only when they
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

VPS sampling and the follow-up deploy on 2026-05-13 moved both known hosts to
`0ff1068`. The 2026-05-14 generated-supply rollout updated the validator host
checkout and validator service only.

| Host | IP | Deployed commit | Running Lemma services |
| --- | --- | --- | --- |
| `lemma-lean-worker-1` | `<validator-host>` | `28fb364` checkout; validator restarted | `lemma-lean-worker-http.service`, `lemma-validator.service`, `lemma-public-dashboard.timer` |
| `lemma-miner-1` | `<miner-host>` | `0ff1068` | `lemma-miner.service`, `lemma-miner3.service`, `lemma-miner4.service`, `lemma-miner5.service`, `lemma-miner6.service`, `lemma-miner7.service` |

Additional evidence: Lean worker health on `127.0.0.1:8787` returned
`{"status": "ok"}`, and `lemma-public-dashboard.service` kept pushing schema 3
refresh commits after the site code deploy. The validator initially failed
closed on stale pins; running the subnet-pins command refreshed the profile and
problem-supply pins, after which startup logged the expected registry hash and
`problem_source=hybrid`. The first observed `0ff1068` round verified/scored 5
proofs with `verify_infra_errors=0`; `set_weights` returned false with the
cleaned message `success=False without message`. The next observed round was an
extreme-split generated theorem that verified/scored 2 proofs and set weights
successfully.

Additional 2026-05-14 validator evidence: the host checkout is `28fb364`;
`.env` pins are profile
`85155229a2c1a0dd9537434d89a7c924368f888e4602b6d909757b09285b0a9c` and
problem-supply
`8b7dccd4fc2a1cf68ad1e1e0ee35ea8680bdc05b24abdb7819ec1dbaee0c1556`;
`lemma-validator.service` is active/running with `NRestarts=0`. A first restart
failed closed after a subnet-pins command was run from the wrong working
directory; rerunning from `/opt/lemma` corrected the pin and startup logged
`problem_source=hybrid`. The first observed post-`28fb364` round used
`theorem_id=gen/7117800`, verified/scored 3 proofs with
`verify_infra_errors=0`, and set weights successfully.

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
