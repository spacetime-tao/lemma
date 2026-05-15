# Lemma Workplan

This is the active tracker for the Lemma repo. Keep it aligned with README, CLI
help, and tests.

## Current Baseline

- Project surface: `lemma`; internal Python package remains `lemma`.
- Default problem source: `LEMMA_PROBLEM_SOURCE=known_theorems`.
- Active supply: [`known_theorems_manifest.json`](../lemma/problems/known_theorems_manifest.json).
- Reward-critical miner artifact: a pre-reveal commitment, then `proof_script`
  plus nonce during reveal.
- Optional portal mining lane: wallet-submitted proof packages can be hosted
  out-of-band, but validators still require the same pre-reveal commitment and
  Lean verification.
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
- Hidden `lemma portal start` service for wallet-submitted miner proofs. It
  verifies submissions with Lean, stores them in SQLite, withholds proof text
  until chain reveal, and serves candidate payloads.
- Shared commitment fixture coverage for Python and the `lemmasub.net` browser
  helper, including portal signing-message parity, so the portal UI cannot drift
  from `lemma/commitments.py` or `lemma/portal.py` unnoticed.
- Optional validator portal candidate lane via `LEMMA_PORTAL_CANDIDATES_URL`.
  Validators map portal hotkeys to registered UIDs, verify the portal hotkey
  signature, re-check the on-chain commitment, dedupe against Axon responses,
  and run the same Lean verification before ledger acceptance.
- Portal fetch/client tests cover current-block query shaping, hidden-proof
  filtering, and malformed candidate-list rejection.
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
  - `lemma portal start`;
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
- Test the `lemmasub.net` `/solve/` frontend against a live testnet portal and
  browser wallets, including chain readback and portal-side on-chain commitment
  gating.
- Add production deployment notes for the portal service after testnet trial:
  TLS/proxy, SQLite backup, and which validator hosts should trust the URL.
- Launch only on a fresh or intentionally reset subnet state.

## Verification Snapshot

- `uv lock`: passed after rename.
- `uv sync --extra dev --extra btcli`: passed.
- `.venv/bin/ruff check lemma tests`: passed.
- `.venv/bin/mypy lemma`: passed (`35 source files`).
- `.venv/bin/pytest tests -q`: passed (`157 passed, 2 skipped`).
- Docker Lean golden: passed (`tests/test_docker_golden.py`, 1 test).
