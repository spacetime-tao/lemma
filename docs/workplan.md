# Lemma Workplan

This is the active tracker for the Lemma repo. Keep it aligned with README, CLI
help, and tests.

## Current Baseline

- Project surface: `lemma`; internal Python package remains `lemma`.
- Default problem source: `LEMMA_PROBLEM_SOURCE=known_theorems`.
- Active supply: [`known_theorems_manifest.json`](../lemma/problems/known_theorems_manifest.json).
- Reward-critical miner artifact: a pre-reveal commitment, then `proof_script`
  plus nonce during reveal.
- Ledger: operator-published JSONL solved-target ledger.
- Solved rows count only when their theorem statement hash matches the current
  manifest.
- Accepted proofs become public replay receipts after validator acceptance.
- Target lifecycle: first target starts at `LEMMA_TARGET_GENESIS_BLOCK`; each
  next target starts at previous `accepted_block + 1`; default commit window is
  `LEMMA_COMMIT_WINDOW_BLOCKS=25`.
- Reward rule: no verified solver means no miner weights; after a solve, the
  current solver set receives miner weight until the next target is solved.
  The earliest valid commitment block wins; same-block valid commitments split.

## Implemented In This Fork

- Public CLI and package metadata use `lemma`.
- Mathlib-only smoke target queue for local protocol testing.
- Known-theorem manifest loader, validation, manifest hash, and deterministic
  target order.
- Solved-ledger helpers and solver weighting by earliest valid commitment block.
- Validator proof mode for `known_theorems`.
- Manual miner submission storage and proof-serving Axon flow.
- `lemma mine` is the guided theorem-to-proof path: it verifies by default,
  publishes the compact commitment, and starts the miner.
- `lemma submit` remains as a hidden advanced command for scripts that only need
  to verify and store a proof.
- `lemma commit --problem <target-id>` retries a stored proof commitment.
- Miner reveal gating: no proof text during commit phase; proof, nonce, and
  commitment hash only during reveal phase.
- Validator commitment checks reject missing, late, malformed, copied, wrong
  target, wrong nonce, and wrong proof-hash commitments before Lean verification.
- Static public miner dashboard export from the known-theorem manifest and
  solved ledger, including schema 3 accepted-proof replay receipts.
- Public CLI:
  - `lemma setup`;
  - `lemma mine`;
  - `lemma status`;
  - `lemma validate`.
- Hidden advanced/script CLI:
  - `lemma target show`;
  - `lemma target ledger`;
  - `lemma submit`;
  - `lemma commit --problem <target-id>`;
  - `lemma verify --problem <target-id> --submission <Submission.lean>`;
  - `lemma miner start`;
  - `lemma dashboard export --output <path>`;
  - `lemma validator check`;
  - `lemma validator start`;
  - `lemma validator dry-run`;
  - `lemma meta`.
- Startup/profile/subnet-pin checks for `known_theorems_manifest_sha256`.
- Legacy LLM prover, judge, scoring, generated/hybrid/frozen source, Formal
  Conjectures runtime, miner attest, training-export, miner-gating, public-IP
  discovery, and knowledge-base paths removed from trunk.

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
- Decide how the operator will publish and sign the solved-target ledger.
- Launch only on a fresh or intentionally reset subnet state.

## Verification Snapshot

- `uv lock`: passed after rename.
- `uv sync --extra dev --extra btcli`: passed.
- `.venv/bin/ruff check lemma tests`: passed.
- `.venv/bin/mypy lemma`: passed (`34 source files`).
- `.venv/bin/pytest tests -q`: passed (`136 passed, 2 skipped`).
- Docker Lean golden: passed (`tests/test_docker_golden.py`, 1 test).
