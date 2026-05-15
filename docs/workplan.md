# Lemma Workplan

This is the active tracker for the Lemma repo. Keep it aligned with README, CLI
help, tests, and the public site.

## Current Baseline

- Project surface: `lemma`; internal Python package remains `lemma`.
- Default problem source: `LEMMA_PROBLEM_SOURCE=known_theorems`.
- Active cadence supply: [`known_theorems_manifest.json`](../lemma/problems/known_theorems_manifest.json).
- Reward-critical miner artifact: a pre-reveal commitment, then `proof_script`
  plus nonce during reveal.
- Ledger: operator-published JSONL solved-target ledger.
- Solved rows count only when their theorem statement hash matches the current
  manifest.
- Accepted proofs become public replay receipts after validator acceptance.
- Target lifecycle: first target starts at `LEMMA_TARGET_GENESIS_BLOCK`; each
  next target starts at previous `accepted_block + 1`; default commit window is
  `LEMMA_COMMIT_WINDOW_BLOCKS=25`.
- Reward rule: current-epoch verified cadence work earns
  `(1 - solve_fraction)^2`, ranked by commitment block; unearned weight routes
  to `LEMMA_OWNER_BURN_UID`.
- Formal Conjectures campaigns are manual owner-emission bounties. They use the
  campaign registry and append-only campaign ledger, but do not affect validator
  `set_weights`.

## Implemented In This Fork

- Public CLI and package metadata use `lemma`.
- Mathlib-only smoke target queue for local protocol testing.
- Known-theorem manifest loader, validation, manifest hash, and deterministic
  target order.
- Solved-ledger helpers and accepted-proof replay receipts.
- Validator proof mode for `known_theorems`.
- Current-epoch cadence reward math with owner/burn remainder.
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
- Formal Conjectures campaign registry helpers:
  - `lemma/formal_conjectures_campaigns.json`;
  - `lemma/formal_campaigns.py`;
  - append-only manual acceptance ledger rows with
    `manual_winner_take_all_owner_emission`.
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
- Browser solve portal, portal backend, portal validator candidate lane,
  generated/hybrid/frozen runtime, legacy LLM prover, judge scoring, miner
  attest, training-export, miner-gating, public-IP discovery, and knowledge-base
  paths are not part of the current trunk.

## Next Work

- Replace smoke targets with serious cadence targets from generated builders,
  curated theorem lists, papers, textbooks, Formal Abstracts-style statements,
  or mathlib gap lists.
- Add the next generated-cadence source in a small slice if we want recurring
  generated traffic again; keep builder ordering append-only and test normalized
  theorem-shape diversity.
- Add a small repo-local target intake checklist for duplicate search,
  statement-faithfulness review, citation review, and Lean `sorry` build check.
- Select initial Formal Conjectures campaigns from
  `https://google-deepmind.github.io/formal-conjectures/data/conjectures.json`,
  pin upstream commit/file/declaration, then fill the campaign registry.
- Decide how the operator will publish and sign both the solved-target ledger
  and the manual campaign acceptance ledger.
- Launch only on a fresh or intentionally reset subnet state.

## Verification Snapshot

- Focused pivot check:
  `.venv/bin/pytest tests/test_rewards.py tests/test_validator_epoch_hardening.py tests/test_cli_surface.py tests/test_commitments.py -q`
  passed (`67 passed`).
- Formal campaign check:
  `.venv/bin/pytest tests/test_formal_campaigns.py tests/test_rewards.py -q`
  passed (`8 passed`).
