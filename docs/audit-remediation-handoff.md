# Audit remediation handoff

Use this file if chat context compacts or a future agent needs the current
state quickly. Start here, then read [`local handoff note`](../local handoff note) and
[`docs/workplan.md`](workplan.md).

## Current state

- Working tree: `LOCAL_WORKSPACE/lemma` on `main`, tracking `origin/main`.
- Latest runtime batch covered by this handoff is `0ff1068` (`Record CI
  evidence for set_weights cleanup`) after the 2026-05-13 lemmasub.net
  dashboard plus droplet audit follow-up.
- Base commit before the earlier audit-remediation patch: `9546095`
  (`Track live ops hardening backlog`).
- Current audit target: strict local subnet-quality pass for binary Lean proof
  grading. Live VPS/testnet mutation was out of scope.
- Refreshed audit doc: [`docs/codex-audit.md`](codex-audit.md), rating
  `8.4 / 10`.
- Latest GitHub-confirmed runtime head: `0ff1068` (`Record CI evidence for
  set_weights cleanup`), with `CI` passing on GitHub Actions run
  `25793725075`. The preceding code commit `d95411b` also had `CI` and
  `Build and Push Docker Image` passing on runs `25793209291` and
  `25793209296`.
- Current testnet Droplet head: `0ff1068` on both known hosts.

## Implemented in the current local patch

- Generated supply adds a rare `extreme` split: 85 builders total with
  10 / 35 / 50 / 5 easy / medium / hard / extreme weights.
- The curated catalog includes positive-weight `extreme` rows, and hybrid
  sampling picks the split before the generated/catalog lane.
- Validator timeout policy includes `LEMMA_TIMEOUT_SPLIT_EXTREME_MULT`; the
  validator profile schema is bumped to `lemma_validator_profile_v7`, and
  `.env.example` lists the extreme multiplier alongside the other split knobs.

## Implemented in the earlier audit-remediation patch

- Training export `OSError` is non-fatal after scoring; `set_weights` can still
  run with known scores.
- `LEMMA_VALIDATOR_MIN_FREE_BYTES` skips validator epochs before miner queries
  when root/cache free space is too low.
- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES` adds total byte pruning to the warm Lean
  workspace cache.
- Verifier-local `timeout`, `oom`, `docker_error`, and `remote_error` are
  recorded as validator infra failures, exported via `verify_infra_error_uids`,
  and excluded from miner verify-credibility downgrades.
- Ordinary all-fail Lean proof epochs persist verify-credibility downgrades.
- Validator service catches cadence/RPC errors in-loop; HTTP 429/rate-limit
  messages back off longer.
- Public dashboard refresh uses `flock` and cleans temp files.
- Legacy live-adjacent surfaces are retired:
  `reasoning_only`, `LEMMA_JUDGE_PROFILE_ATTEST_*`,
  `JUDGE_PROFILE_SHA256_EXPECTED`, `/lemma/judge_profile_sha256`.
- Runtime asserts and silent broad cleanup exceptions were removed where they
  obscured behavior.
- Follow-up after live read-only sampling: `set_weights` result handling now
  treats tuple-style false returns and raised RPC exceptions as failures, retries
  them, and logs a concrete final message.
- Follow-up after the lemmasub.net/droplet audit: false/no-message set-weights
  returns now normalize to `success=False without message` instead of tuple noise
  such as `(False, None)`.

## Current focused verification

- `.venv/bin/ruff check lemma tests tools`: passed.
- `.venv/bin/mypy lemma`: passed.
- `.venv/bin/pytest tests -q`: passed, `314 passed, 2 skipped, 12 warnings`.
- `.venv/bin/python scripts/ci_verify_generated_templates.py`: passed,
  `OK: generated template metadata/witness gate covered 85 builders`.
- `git diff --check`: passed.

## Docker evidence

Docker Desktop is now reachable from an escalated shell:

```text
Server Version: 29.4.2
Operating System: Docker Desktop
Architecture: aarch64
CPUs: 10
Total Memory: 7.75GiB
```

- `docker image inspect lemma/lean-sandbox:latest`: image present
  (`lemma/lean-sandbox:latest`, `lemma/lean-sandbox:mathlib-5450b53e`).
- `RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/python scripts/ci_verify_generated_templates.py`:
  passed; all 85 generated template stubs and witnesses built in one Docker
  workspace.

## Next decisions

- Watch the first full `0ff1068` post-deploy rounds and record
  set-weights/emission movement.
- Add production alerts for failed services, high disk, missing epoch summaries,
  repeated skipped weights, and repeated set_weights failures.
- Plan a separate Lean cache volume or partition for validator/worker hosts.

## Live read-only evidence

Sampling on 2026-05-13 used `tools.ops_dashboard` plus direct SSH reads only; no
services were restarted or changed.

- Validator / Lean worker `<validator-ssh-host>`: deployed `d42addb`,
  `lemma-validator` and `lemma-lean-worker-http` active, root/cache filesystem
  `33%` used, Lean worker health `{"status": "ok"}`.
- Miner host `<miner-ssh-host>`: deployed `d42addb`, six miner services
  active, six axon ports open, root filesystem `23%` used.
- Fresh sampled validator round at `2026-05-13 06:44 UTC`:
  `theorem_id=gen/7110900`, `verified=5`, `scored=5`, no reject counters,
  `seconds=554.74`; old deployed code then logged `set_weights success=False
  message=None` after retries.

## Live deploy evidence

On 2026-05-13, after explicit live-ops go-ahead, both known Droplets were
fast-forwarded from `d42addb` to `8067b70`. The validator was paused during the
deploy; miners and Lean worker were restarted; validator was started last.

- Validator / Lean worker `<validator-ssh-host>`: deployed `8067b70`,
  `lemma-validator` and `lemma-lean-worker-http` active, root/cache filesystem
  `38%` used, Lean worker health `{"status": "ok"}`.
- Miner host `<miner-ssh-host>`: deployed `8067b70`, six miner services
  active, six axon ports open, root filesystem `23%` used.
- First post-deploy validator round at `2026-05-13 07:30 UTC`:
  `theorem_id=curated/foundations/list_append_nil_induction`, `verified=3`,
  `scored=3`, `verify_infra_errors=0`, no reject counters, `seconds=369.99`,
  and `set_weights success=True`.

## Live read-only droplet audit follow-up

Sampling on 2026-05-13 at about 10:18 UTC was read-only; no services were
restarted or changed.

- Validator / Lean worker `<validator-ssh-host>`: deployed `8067b70`,
  `lemma-validator` and `lemma-lean-worker-http` active, root/cache filesystem
  `28%` used, Lean worker health on `127.0.0.1:8787` returned
  `{"status":"ok"}`.
- Public dashboard publisher on the validator host: timer enabled/running, path
  inactive, service completed successfully and pushed refresh commits through
  `9c31c1e` during the audit window.
- Miner host `<miner-ssh-host>`: deployed `8067b70`, six miner services
  active, root filesystem `23%` used.
- Latest sampled validator round at `2026-05-13 10:04 UTC` verified/scored `4`
  proofs with `verify_infra_errors=0` and `set_weights success=True`. Earlier
  rounds still logged intermittent `set_weights success=False message=(False,
  None)` when Bittensor returned false without a message; the follow-up patch
  below is now deployed at `0ff1068`.

## Live deploy to current head

On 2026-05-13, both known Droplets were fast-forwarded from `8067b70` to
`0ff1068`. The validator was stopped first; the miner host, Lean worker, miner
services, and validator were then restarted in order.

- Validator / Lean worker `<validator-ssh-host>`: deployed `0ff1068`;
  `lemma-validator`, `lemma-lean-worker-http`, and
  `lemma-public-dashboard.timer` active; Lean worker health on
  `127.0.0.1:8787` returned `{"status": "ok"}`.
- Miner host `<miner-ssh-host>`: deployed `0ff1068`; six miner services
  active.
- The first validator restart failed closed because the old
  `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED` pin did not match the profile after
  the extreme-split supply change. Running
  `lemma configure subnet-pins --env-file /opt/lemma/.env --yes` wrote profile
  pin `85155229a2c1a0dd9537434d89a7c924368f888e4602b6d909757b09285b0a9c` and
  problem-supply pin
  `f4ae425ad437c97b00d47b7ba97f97e1ff4cec8d5d66290c8b2364d91f822311`.
- After the pin update, validator startup logged the expected registry hash,
  `problem_source=hybrid`, and `validator cadence follows problem seed windows`.
- First observed post-`0ff1068` validator round completed at
  `2026-05-13 10:59 UTC`: `theorem_id=gen/7112100`, split `medium`,
  `verified=5`, `scored=5`, `verify_infra_errors=0`, no reject counters.
  `set_weights` returned false after three attempts, but the deployed cleanup
  logged `success=False without message` instead of `(False, None)`.
- Next live task: watch follow-up rounds for successful `set_weights`,
  reveal/emission movement, and any repeated false/no-message RPC pattern.
