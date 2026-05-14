# Lemma Workplan

This is the active tracker for the Lemma repo. Keep it aligned with README, CLI
help, and tests.

## Current Baseline

- Project surface: `lemma`; internal Python package remains `lemma`.
- Default problem source: `LEMMA_PROBLEM_SOURCE=known_theorems`.
- Active supply: [`known_theorems_manifest.json`](../lemma/problems/known_theorems_manifest.json).
- Reward-critical miner artifact: `proof_script` only.
- Ledger: operator-published JSONL solved-target ledger.
- Reward rule: no verified solver means no miner weights; after a solve, the
  current solver set receives miner weight until the next target is solved.
  Same-batch solvers split that weight equally.

## Implemented In This Fork

- Public CLI and package metadata use `lemma`.
- Mathlib-only smoke target queue for local protocol testing.
- Known-theorem manifest loader, validation, manifest hash, and deterministic
  target order.
- Solved-ledger helpers and solver weighting with equal same-batch tie splits.
- Validator proof mode for `known_theorems`.
- Manual miner submission storage and proof-serving Axon flow.
- `lemma submit` verifies by default and prints validity/serving confirmation.
- Static public miner dashboard export from the known-theorem manifest and
  solved ledger.
- CLI:
  - `lemma target show`;
  - `lemma target ledger`;
  - `lemma submit --problem <target-id> --submission <Submission.lean>`;
  - `lemma verify --problem <target-id> --submission <Submission.lean>`;
  - `lemma miner start`;
  - `lemma dashboard export --output <path>`;
  - `lemma validator check`;
  - `lemma validator start`;
  - `lemma validator dry-run`;
  - `lemma meta`.
- Startup/profile/subnet-pin checks for `known_theorems_manifest_sha256`.
- Legacy LLM prover, judge, scoring, generated/hybrid/frozen source, Formal
  Conjectures runtime, commit reveal, miner attest, training-export, miner-gating,
  public-IP discovery, and knowledge-base paths removed from trunk.

## Next Work

- Replace smoke targets with serious curated targets from papers, textbooks,
  Formal Abstracts-style statements, or mathlib gap lists.
- Add a small repo-local target intake checklist for duplicate search,
  statement-faithfulness review, citation review, and Lean `sorry` build check.
- Use Formal Conjectures for discovery via
  `https://google-deepmind.github.io/formal-conjectures/data/conjectures.json`.
  Current no-formal-proof pools: `research open` 1,070, `textbook` 134,
  `test` 472. Filter primarily for `category="research open"` and inspect
  source files; `hasFormalProof=false` only means the site has no external
  formal-proof reference.
- Add public solved-proof references: publish accepted `Submission.lean`
  artifacts and record their URLs in the solved-target ledger.
- Decide how the operator will publish and sign the solved-target ledger.
- Launch only on a fresh or intentionally reset subnet state.

## Verification Snapshot

- `uv lock`: passed after rename.
- `uv sync --extra dev --extra btcli`: passed.
- `.venv/bin/ruff check lemma tests`: passed.
- `.venv/bin/mypy lemma`: passed (`32 source files`).
- `.venv/bin/pytest tests -q`: passed (`91 passed, 2 skipped`).
- Docker Lean golden: passed (`tests/test_docker_golden.py`, 1 test).
