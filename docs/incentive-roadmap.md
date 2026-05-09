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

- [x] **Proof intrinsic (partial)** — Lean `--` / `/- … -/` stripped before the heuristic (`LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS`, default on). Default **`LEMMA_SCORE_PROOF_WEIGHT=0.10`** keeps the text heuristic low-weight. Decision note: [proof-intrinsic-decision.md](proof-intrinsic-decision.md). Compare-only Lean probe: `LEMMA_LEAN_PROOF_METRICS=1` adds `proof_metrics` to `VerifyResult`; initial calibration is recorded. **Still open:** validate a Lean/elaborator-backed replacement before any scoring change; do not add more regex padding checks.
- [x] **Credibility multiplier** — Per-UID verify-pass EMA persisted in reputation JSON; score uses `(credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)` after EMA smoothing (`LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA`, default 0.08; set alpha to **0** to freeze credibility updates). Default exponent remains **1.0** until calibrated; the KB `2.5` target is documented as a policy candidate in [credibility-exponent-decision.md](credibility-exponent-decision.md). Credibility is not a Lean-valid padding detector; proof-quality replacement work stays under [proof-intrinsic-decision.md](proof-intrinsic-decision.md).
- [x] **Training export** — Documented gaming/leakage ([training_export.md](training_export.md)); **`LEMMA_TRAINING_EXPORT_PROFILE=reasoning_only`** omits proof, proof metrics, judge rubric, and Pareto weights (`lemma/validator/training_export.py`).

### Problem supply & predictability

- [x] **Template / seed predictability** — Default: **SHA256-mix** chain seed before template `random.Random` (`expand_seed_for_problem_rng` in `lemma/problems/generated.py`); ids stay `gen/<seed>`. **Public** seed→theorem map remains deterministic (precompute still possible). Rollback: **`LEMMA_GENERATED_LEGACY_PLAIN_RNG=1`**. See [catalog-sources.md](catalog-sources.md).
- [x] **`LEMMA_PROBLEM_SOURCE=frozen` (miniF2F)** — Fail-closed unless **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (`get_problem_source`, `validator-check`).

### Validator protocol & fairness

- [x] **`deadline_block` enforcement** — Validator drops responses when chain head ≥ synapse `deadline_block` after the forward returns.
- [x] **Cross-validator problem alignment** — **`LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS`** subtracts from RPC head before seed + forward deadline (`effective_chain_head_for_problem_seed`); CLI/status/rehearsal paths aligned. See [catalog-sources.md](catalog-sources.md).
- [x] **Workspace cache key** — Optional **`LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH=1`**: cache slot includes truncated SHA256 of `Submission.lean` (`workspace_verify_cache_key` in `lemma/lean/workspace.py`). Default off (template-only key; faster reuse).

### Trust & sybil

- [x] **Sybil economics** — Operator guide [sybil_economics.md](sybil_economics.md): Lemma dedup vs coldkey sybil realities, UID pressure; tie-break / stake policy remains subnet governance ([`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml)).
- [ ] **Judge / infra trust** — HTTP peer quorum for **`judge_profile_sha256`** ships (`LEMMA_JUDGE_PROFILE_ATTEST_*`). Still open: stronger attestations (e.g. on-chain), operational hardening beyond URL probes.

### Compute placement

- [x] **Validator Lean load** — [validator_lean_load.md](validator_lean_load.md): concurrency caps, **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** trust vs CPU, remote verify worker; aligns with [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) `compute_distribution`.

### Transport (long-term)

- [x] **Axon/Dendrite** — [transport.md](transport.md): current Dendrite/synapse + body-hash integrity; relation to `knowledge/subnet.invariants.yaml` deprecation for **new** designs vs Lemma’s shipping stack.

### Judge input robustness

- [x] **Trace/Judge parsing** — `parse_rubric_json` prefers brace-balanced spans that open like `{"coherence"|"exploration"|"clarity"` before naive first-`{` slicing; invalid dict-shaped candidates are skipped so a later valid rubric object can win. Determined injection remains model-strength dependent.

---

## Plumbing / cleanup (lower urgency than mechanism gaps)

Track in issues or refactors as capacity allows: consolidate CLI dry-run paths, thin `validator/query.py`, merge duplicate startup checks (`validator_check` vs `service`), single Lake-cache policy env, optional catalog split (`lemma/catalog/` dev vs runtime), etc.

---

## References

- Non-overlapping cleanup and repo-split plan: [workplan.md](workplan.md)
- Full external-audit remediation checklist (prioritized): [audit-remediation.md](audit-remediation.md)
- Implementation map: [incentive_migration.md](incentive_migration.md)
- Proof intrinsic scoring decision: [proof-intrinsic-decision.md](proof-intrinsic-decision.md)
- Credibility exponent decision: [credibility-exponent-decision.md](credibility-exponent-decision.md)
- Scoring entrypoint: `lemma/scoring/rewards.py`, `lemma/scoring/proof_intrinsic.py`
- Epoch loop: `lemma/validator/epoch.py`
