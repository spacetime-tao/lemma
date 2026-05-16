# Lemma Workplan

This is the active tracker for the Lemma repo. Keep it aligned with README, CLI
help, tests, and the public site.

## Current Baseline

- Project surface: `lemma`; internal Python package remains `lemma`.
- Default problem source: `LEMMA_PROBLEM_SOURCE=hybrid`.
- Active cadence supply: curated
  [`known_theorems_manifest.json`](../lemma/problems/known_theorems_manifest.json)
  plus deterministic generated cadence builders.
- Optional prover assistance is OpenAI-compatible and provider-neutral:
  `LEMMA_PROVER_BASE_URL`, `LEMMA_PROVER_API_KEY`, and
  `LEMMA_PROVER_MODEL`; it is not required for manually prepared Lean proofs.
- Reward-critical miner artifact: a pre-reveal commitment, then `proof_script`
  plus nonce during reveal.
- Ledger: operator-published JSONL solved-target ledger.
- Solved rows count only when their theorem statement hash matches the current
  manifest.
- Public cadence export shows task state and solver hotkeys, but not proof
  bodies, proof hashes, proof nonces, or commitment hashes.
- Public live JSON is generated on the validator droplet with
  `lemma dashboard publish --output-dir /var/www/lemma-live`.
- Target lifecycle: first target starts at `LEMMA_TARGET_GENESIS_BLOCK`; each
  next target starts at previous `accepted_block + 1`; default commit window is
  `LEMMA_COMMIT_WINDOW_BLOCKS=25`.
- Reward rule: current-epoch verified cadence work earns
  `(1 - solve_fraction)^2`, ranked by commitment block; unearned weight routes
  to `LEMMA_OWNER_BURN_UID`.
- Formal Conjectures campaigns are manual owner-emission bounties. They use the
  campaign registry and append-only campaign ledger, but do not affect validator
  `set_weights`. Bounty winner identity is hotkey-first; UID is optional.

## Implemented In This Fork

- Public CLI and package metadata use `lemma`.
- Mathlib-only smoke target queue for local protocol testing.
- Known-theorem manifest loader, validation, manifest hash, and deterministic
  target order.
- Solved-ledger helpers and public accepted-solver rows.
- Validator proof mode for `known_theorems`.
- Current-epoch cadence reward math with owner/burn remainder.
- Manual miner submission storage and proof-serving Axon flow.
- `lemma mine` is the guided theorem-to-proof path: it runs miner preflight,
  verifies by default, publishes the compact commitment, and starts the miner.
- `lemma submit` remains as a hidden advanced command for scripts that only need
  to verify and store a proof.
- `lemma commit --problem <target-id>` retries a stored proof commitment.
- Miner reveal gating: no proof text during commit phase; proof, nonce, and
  commitment hash only during reveal phase.
- Validator commitment checks reject missing, late, malformed, copied, wrong
  target, wrong nonce, and wrong proof-hash commitments before Lean verification.
- Static/public cadence export from the hybrid cadence source and solved ledger,
  schema 4, with no proof/commit fields.
- Static/public bounty export from the Formal Conjectures campaign registry.
- Atomic live feed publishing for `cadence.json` and `bounties.json`.
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
  - `lemma dashboard export-bounties --output <path>`;
  - `lemma dashboard publish --output-dir <dir>`;
  - `lemma bounty-accept --package <bounty-package.json>`;
  - `lemma validator check`;
  - `lemma validator start`;
  - `lemma validator dry-run`;
  - `lemma meta`.
- Startup/profile/subnet-pin checks for `known_theorems_manifest_sha256`.
- Browser solve portal, portal backend, portal validator candidate lane, legacy
  LLM prover, judge scoring, miner attest, training-export, miner-gating,
  public-IP discovery, and knowledge-base paths are not part of the current
  trunk.

## Next Work

- Broaden generated cadence builders and curated target intake carefully; keep
  builder ordering append-only and test normalized theorem-shape diversity.
- Add a small repo-local target intake checklist for duplicate search,
  statement-faithfulness review, citation review, and Lean `sorry` build check.
- Select initial Formal Conjectures campaigns from
  `https://google-deepmind.github.io/formal-conjectures/data/conjectures.json`,
  pin upstream commit/file/declaration, then fill the campaign registry.
- Deploy `lemma-live-publisher.timer` and nginx for `live.lemmasub.net` on the
  validator droplet.
- Launch only on a fresh or intentionally reset subnet state.

## Verification Snapshot

- `.venv/bin/ruff check lemma tests`
- `.venv/bin/mypy lemma`
- `.venv/bin/pytest tests -q` passed (`163 passed, 2 skipped`).
- Site checks passed:
  `node --check assets/tasks.js`,
  `node --check scripts/check-task-pages.js`,
  `node scripts/check-task-pages.js`.
- Browser QA passed for `/`, `/cadence/`, `/bounties/`, `/setup/`, and `/faq/`
  at desktop and mobile widths with no horizontal overflow; `/setup/` redirects
  home.
