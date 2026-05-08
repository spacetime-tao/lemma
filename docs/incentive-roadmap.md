# Incentive roadmap & checklist

Living tracker for **mechanism work**: what shipped with the hard-migration, what is **reserved** behind env flags, and **known gaps** to close next. For behavior and env details, see [incentive_migration.md](incentive_migration.md).

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

---

## Reserved protocol hooks (declared, fail-fast if enabled)

Validator raises at startup if any of these is set to `1` until implemented—see [incentive_migration.md](incentive_migration.md).

- [ ] `LEMMA_COMMIT_REVEAL_ENABLED` — commit/reveal for anti-leak / copy pools
- [x] `LEMMA_MINER_VERIFY_ATTEST_ENABLED` — Sr25519 hotkey signature + deterministic spot full-verify fraction (`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`; miners require `LEMMA_MINER_LOCAL_VERIFY=1`)
- [ ] `LEMMA_JUDGE_PROFILE_ATTEST_ENABLED` — cross-validator judge profile agreement

---

## Known gaps & planned fixes (prioritized backlog)

Ordered roughly by leverage (design risk first). Check boxes when **merged behavior** matches the intent, not when a draft exists.

### Scoring & objective

- [x] **Proof intrinsic (partial)** — Lean `--` / `/- … -/` stripped before the heuristic (`LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS`, default on). Default **`LEMMA_SCORE_PROOF_WEIGHT=0.35`** favors judge composite over the heuristic. **Still open:** elaborator-backed metrics or further weight tuning.
- [x] **Credibility multiplier** — Per-UID verify-pass EMA persisted in reputation JSON; score uses `(credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)` after EMA smoothing (`LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA`, default 0.08; set to **0** to freeze credibility updates).
- [ ] **Training export** — Revisit what validators emit once intrinsic/scoring stabilize so exports don’t teach deterministic gaming targets.

### Problem supply & predictability

- [ ] **Template / seed predictability** — Expand or diversify problem draws; align reserved hooks with reducing enumerable pools.
- [x] **`LEMMA_PROBLEM_SOURCE=frozen` (miniF2F)** — Fail-closed unless **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (`get_problem_source`, `validator-check`).

### Validator protocol & fairness

- [x] **`deadline_block` enforcement** — Validator drops responses when chain head ≥ synapse `deadline_block` after the forward returns.
- [ ] **Cross-validator problem alignment** — Reduce RPC/skew splits at epoch boundaries (shared quantize / agreed head) so EMA compares like-with-like.
- [ ] **Workspace cache key** — Include submission/proof fingerprint so distinct miners don’t share incremental-build identity incorrectly.

### Trust & sybil

- [ ] **Sybil economics** — Coldkey dedup is not a sybil resistance primitive; evaluate UID-pressure / tie-break policies (e.g. winners-take-most on ties), stake, or other mechanisms documented in `knowledge/sybil.realities.yaml`.
- [ ] **Judge / infra trust** — Strengthen beyond URL + profile hash (attestations, quorum, or miner-verify path once implemented).

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
