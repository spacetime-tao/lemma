# Incentive roadmap & checklist

Living tracker for **mechanism work**: what shipped with the hard-migration, env-gated protocol hooks, and **known gaps** to close next. For behavior and env details, see [incentive_migration.md](incentive_migration.md).

This doc is for **operators and contributors** planning work—not step-by-step exploit writeups. Threat-model specifics belong in private review.

---

## Shipped (hard-migration baseline)

- [x] Strict single-object JSON rubric parse (`judge/json_util.py`) — rejects multi-rubric games
- [x] Fenced miner content + judge prompt treating trace as untrusted data
- [x] Identical-submission dedup (same theorem + proof + trace fingerprint)
- [x] Coldkey dedup (best hotkey per coldkey on metagraph)
- [x] EMA smoothing of reasoning/composite scores (on-disk state)
- [x] Optional multi-theorem epochs (`LEMMA_EPOCH_PROBLEM_COUNT`, default 1)
- [x] Empty-epoch uniform weights exclude own validator UID when possible
- [x] Canonical judge stack pin at validator startup (operator-aligned)
- [x] Generated template registry SHA pin at startup
- [x] Synapse body-hash integrity check when `computed_body_hash` is present
- [x] `LEMMA_JUDGE_PROFILE_ATTEST_ENABLED` — HTTP peer quorum vs local `judge_profile_sha256` (`LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS`, optional `LEMMA_JUDGE_PROFILE_ATTEST_SKIP`); `lemma validator judge-attest-serve`

---

## Known gaps & planned fixes (prioritized backlog)

Ordered roughly by leverage (design risk first). Check boxes when **merged behavior** matches the intent, not when a draft exists.

### Scoring & objective

- [x] **Proof intrinsic (partial)** — Lean `--` / `/- … -/` stripped before the heuristic (`LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS`, default on). Default **`LEMMA_SCORE_PROOF_WEIGHT=0.35`** favors judge composite over the heuristic. **Still open:** elaborator-backed metrics or further weight tuning.
- [x] **Credibility multiplier** — Per-UID verify-pass EMA persisted in reputation JSON; score uses `(credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)` after EMA smoothing (`LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA`, default 0.08; set to **0** to freeze credibility updates).
- [x] **Training export** — Documented gaming/leakage ([training_export.md](training_export.md)); **`LEMMA_TRAINING_EXPORT_PROFILE=reasoning_only`** omits proof, judge rubric, and Pareto weights (`lemma/validator/training_export.py`).

### Problem supply & predictability

- [x] **Template / seed predictability** — Default: **SHA256-mix** chain seed before template `random.Random` (`expand_seed_for_problem_rng` in `lemma/problems/generated.py`); ids stay `gen/<seed>`. **Public** seed→theorem map remains deterministic (precompute still possible). Rollback: **`LEMMA_GENERATED_LEGACY_PLAIN_RNG=1`**. See [catalog-sources.md](catalog-sources.md).
- [x] **`LEMMA_PROBLEM_SOURCE=frozen` (miniF2F)** — Fail-closed unless **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (`get_problem_source`, `validator-check`).

### Validator protocol & fairness

- [x] **`deadline_block` enforcement** — Validator drops responses when chain head ≥ synapse `deadline_block` after the forward returns.
- [x] **Cross-validator problem alignment** — **`LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS`** subtracts from RPC head before seed + forward deadline (`effective_chain_head_for_problem_seed`); CLI/status/rehearsal paths aligned. See [catalog-sources.md](catalog-sources.md).
- [x] **Workspace cache key** — Optional **`LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH=1`**: cache slot includes truncated SHA256 of `Submission.lean` (`workspace_verify_cache_key` in `lemma/lean/workspace.py`). Default off (template-only key; faster reuse).

### Trust & sybil

- [ ] **Sybil economics** — Coldkey dedup is not a sybil resistance primitive; evaluate UID-pressure / tie-break policies (e.g. winners-take-most on ties), stake, or other mechanisms documented in `knowledge/sybil.realities.yaml`.
- [ ] **Judge / infra trust** — HTTP peer quorum for **`judge_profile_sha256`** ships (`LEMMA_JUDGE_PROFILE_ATTEST_*`). Still open: stronger attestations (e.g. on-chain), operational hardening beyond URL probes.

### Compute placement

- [ ] **Validator Lean load** — Lower **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** only after miners run attest + local verify; document trust vs CPU tradeoffs (`knowledge/subnet.invariants.yaml` compute distribution).

### Transport (long-term)

- [ ] **Axon/Dendrite** — Document current synapse + body-hash rationale; plan HTTP + Epistula (or successor) when feasible (`knowledge/subnet.invariants.yaml` deprecation note).

### Judge input robustness

- [ ] **Trace/Judge parsing** — Reduce silent drops when honest traces contain brace-heavy math notation; strengthen defenses beyond fencing for determined injection (model-strength dependent today).

---

## Plumbing / cleanup (lower urgency than mechanism gaps)

Track in issues or refactors as capacity allows: consolidate CLI dry-run paths, thin `validator/query.py`, merge duplicate startup checks (`validator_check` vs `service`), single Lake-cache policy env, optional catalog split (`lemma/catalog/` dev vs runtime), etc.

---

## References

- Implementation map: [incentive_migration.md](incentive_migration.md)
- Reserved flags module: `lemma/validator/protocol_migration.py`
- Scoring entrypoint: `lemma/scoring/rewards.py`, `lemma/scoring/proof_intrinsic.py`
- Epoch loop: `lemma/validator/epoch.py`
