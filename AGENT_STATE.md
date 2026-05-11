# Agent State

This is the handoff note for chat freezes, context loss, and future agents.
Keep it short, current, and useful. The active work tracker is
[`docs/workplan.md`](docs/workplan.md).

## Working Mentality

Treat every line of code as a liability. Every line must be maintained,
reviewed, tested, and understood. Prefer lean changes that fix the underlying
shape of the system over extra layers of checks, guards, or compensating logic.

## Current Direction

Lemma's live reward axis is binary proof verification:

- a miner submits `proof_script`;
- the validator checks that proof against the published theorem with Lean;
- a proof that verifies can enter scoring;
- a proof that fails verification does not enter scoring.

Informal reasoning and optional prose-judge tooling are out-of-band. Do not add
reasoning prose, subjective judge scores, or proof-efficiency heuristics back
into the live reward path without a separate product decision.

## Current Repository State

- Working checkout: `/Users/leehall/lemma`.
- Local branch: `main` tracking `origin/main`.
- Current local/GitHub head during this audit:
  `b7088f00295fe0e23ad4a856ac43799b9acd8882`
  (`Remove stale judge config from proof-only path`).
- Current GitHub failure before this handoff update:
  - CI run `25649757216` failed in `uv sync --extra dev`.
  - Docker publish run `25649757232` failed in `pip install .`.
  - Root cause: `pyproject.toml` added a direct-reference `cli` extra for
    `lemma-cli` without Hatch metadata
    `allow-direct-references = true`.
- Local fix in this working tree: `[tool.hatch.metadata]`
  `allow-direct-references = true`.

## Local Verification Snapshot

Current local baseline after the metadata fix on 2026-05-11:

- `uv sync --extra dev`: passed after sandbox escalation for the uv cache path.
- `uv run ruff check lemma tests tools`: passed.
- `uv run pytest tests/ -q --ignore=tests/test_docker_golden.py`:
  `255 passed, 1 skipped, 12 warnings`.
- `uv run python scripts/ci_verify_generated_templates.py`:
  `OK: generated template metadata gate covered 40 builders`.
- `RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest uv run pytest tests/test_docker_golden.py -v --tb=short`:
  `1 passed in 210.60s`.
- `docker build -f Dockerfile -t lemma-runtime:ci-smoke .`: passed.
- `uv run mypy lemma`: non-blocking quality gap,
  `70 errors in 11 files`.

## VPS Status Snapshot

Do not deploy or restart services during the current docs/CI-fix pass.

- `lemma-lean-worker-1` (`167.99.145.132`):
  - SSH responded with uptime.
  - `/opt/lemma` deployed commit: `82bba8d`.
  - Active services: `lemma-lean-worker-http.service`,
    `lemma-validator.service`.
- `lemma-miner-1` (`161.35.50.115`):
  - SSH responded with uptime.
  - `/opt/lemma` deployed commit: `82bba8d`.
  - Active services: `lemma-miner.service`, `lemma-miner3.service`,
    `lemma-miner4.service`, `lemma-miner5.service`, `lemma-miner6.service`,
    `lemma-miner7.service`.

Both droplets are alive but one commit behind `main` at `b7088f0`. This is
record-only for the current pass.

## Where To Work

- Active work tracker: [`docs/workplan.md`](docs/workplan.md).
- Proof objective: [`docs/objective-decision.md`](docs/objective-decision.md).
- Proof-verification incentives:
  [`docs/proof-verification-incentives.md`](docs/proof-verification-incentives.md).
- Testing commands: [`docs/testing.md`](docs/testing.md).
- VPS/key custody: [`docs/vps-safety.md`](docs/vps-safety.md).

## Rules For Future Agents

- Preserve proof-verification language: pass or fail, binary system.
- Keep `spacetime-tao/lemma` focused on consensus-critical code.
- Keep friendly operator UX in `lemma-cli` unless the core repo needs a minimal
  compatibility shim.
- Use tests and real logs before changing mechanism code.
- Avoid defensive complexity where a simpler data model or call path can make
  invalid states impossible.
