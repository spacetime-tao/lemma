# Audit remediation handoff

Use this file if chat context compacts or a future agent needs the current
state quickly. Start here, then read [`local handoff note`](../local handoff note) and
[`docs/workplan.md`](workplan.md).

## Current state

- Working tree: `LOCAL_WORKSPACE/lemma` on `main`, tracking `origin/main`.
- Base commit before this local patch: `9546095` (`Track live ops hardening backlog`).
- Current audit target: strict local subnet-quality pass for binary Lean proof
  grading. Live VPS/testnet mutation was out of scope.
- Refreshed audit doc: [`docs/codex-audit.md`](codex-audit.md), rating
  `8.4 / 10`.

## Implemented in this local patch

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

## Verification already run

- `.venv/bin/ruff check lemma tests tools`: passed.
- `.venv/bin/mypy lemma`: passed.
- `.venv/bin/pytest tests -q`: passed, `307 passed, 2 skipped, 12 warnings`.
- `.venv/bin/python scripts/ci_verify_generated_templates.py`: passed,
  `OK: generated template metadata/witness gate covered 80 builders`.
- `.venv/bin/bandit -q -r lemma -ll`: passed.
- `.venv/bin/bandit -q -r lemma`: 20 low findings only.
- `.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969`:
  passed with `No known vulnerabilities found, 3 ignored`.

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
- `RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/pytest tests/test_docker_golden.py -v --tb=short`:
  passed, `1 passed in 208.57s`.
- `RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/python scripts/ci_verify_generated_templates.py`:
  passed; all 80 generated template stubs and witnesses built in one Docker
  workspace.
- `docker build -f Dockerfile -t lemma-runtime:ci-smoke .`: passed.

## Next decisions

- Commit this patch locally.
- Push and check GitHub Actions, especially `docker-lean-sandbox`.
- Then run a live testnet evidence slice: miner latency, prover latency,
  validator Lean verify time, scored miner count, skip reasons, `set_weights`,
  and emission movement.
