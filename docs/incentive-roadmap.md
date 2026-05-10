# Incentive roadmap & checklist

Living tracker for **mechanism work**: what shipped with the hard-migration, env-gated protocol hooks, and **known gaps** to close next. For behavior and env details, see [incentive_migration.md](incentive_migration.md).

This doc is for **operators and contributors** planning work—not step-by-step exploit writeups. Threat-model specifics belong in private review.

---

## Shipped (hard-migration baseline)

- [x] Strict single-object JSON rubric parse (`judge/json_util.py`) — rejects multi-rubric games
- [x] Fenced miner content + judge prompt treating trace as untrusted data
- [x] Identical-submission dedup (same normalized theorem + proof + trace fingerprint)
- [x] Coldkey dedup (best hotkey per coldkey on metagraph)
- [x] EMA smoothing of reasoning/composite scores (on-disk state)
- [x] Optional multi-theorem epochs (`LEMMA_EPOCH_PROBLEM_COUNT`, default 1)
- [x] Empty-epoch uniform weights exclude own validator UID when possible
- [x] Canonical judge stack pin at validator startup (operator-aligned)
- [x] Generated template registry SHA pin at startup
- [x] Synapse body-hash integrity fails closed when `computed_body_hash` is missing/mismatched or `deadline_block` is missing
- [x] `LEMMA_JUDGE_PROFILE_ATTEST_ENABLED` — HTTP peer quorum vs local `judge_profile_sha256` (`LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS`, optional `LEMMA_JUDGE_PROFILE_ATTEST_SKIP`); `lemma validator judge-attest-serve`

---

## Known gaps & planned fixes (prioritized backlog)

Ordered roughly by leverage (design risk first). Check boxes when **merged behavior** matches the intent, not when a draft exists.

### Scoring & objective

- [x] **One-sentence objective** — Current objective: Lemma incentivizes miners to produce Lean-valid mathematical proofs for published theorem statements. Decision note: [objective-decision.md](objective-decision.md). Judged reasoning remains a current bootstrap ranking layer for Lean-valid submissions.
- [x] **Proof intrinsic (partial)** — Lean `--` / `/- … -/` plus empty lines are stripped before the heuristic (`LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS`, default on). Default **`LEMMA_SCORE_PROOF_WEIGHT=0.10`** keeps the text heuristic low-weight. Decision note and decision-record template: [proof-intrinsic-decision.md](proof-intrinsic-decision.md). Compare-only Lean probe: `LEMMA_LEAN_PROOF_METRICS=1` adds `proof_metrics` to `VerifyResult`; v2 calibration is recorded; private exports carry non-secret profile/registry provenance; the offline analyzer now separates failed probe rows from successful calibration data, reports data-readiness blockers including same-theorem comparison coverage and mixed profile hashes, prints concrete `decision_data_gaps`, prints within-theorem centered correlations and disagreement candidates, prints a conservative gate verdict, and supports `--require-decision-ready` for release checklists. **Still open:** collect a real export that clears readiness blockers, pass the proof-side go/no-go gate, then explicitly replace, keep low, or remove/reduce the heuristic; do not add more regex padding checks.
- [x] **Judge incentive role** — Current stance: the LLM judge is a bootstrap signal for Lean-valid submissions, not a declared permanent objective. Decision note and decision-record template: [judge-incentive-decision.md](judge-incentive-decision.md). **Still open:** governance must explicitly choose permanent judge, capped/bootstrap judge, or judge-free scoring before live reward changes.
- [x] **Credibility multiplier** — Per-UID verify-pass EMA persisted in reputation JSON; score uses `(credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)` after EMA smoothing (`LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA`, default 0.08; set alpha to **0** to freeze credibility updates). Default exponent remains **1.0** until calibrated; the KB `2.5` target is documented as a policy candidate in [credibility-exponent-decision.md](credibility-exponent-decision.md). Credibility is not a Lean-valid padding detector; proof-quality replacement work stays under [proof-intrinsic-decision.md](proof-intrinsic-decision.md).
- [x] **Training export** — Documented gaming/leakage, proof-metrics calibration, and sybil/Pareto replay collection ([training_export.md](training_export.md)); private `full` exports include theorem statement, proof, coldkey when available, judge rubric, proof metrics, non-secret profile/registry provenance, and Pareto weights for offline analysis. **`LEMMA_TRAINING_EXPORT_PROFILE=reasoning_only`** omits the sensitive proof/label/replay fields but keeps non-secret provenance (`lemma/validator/training_export.py`).

### Problem supply & predictability

- [x] **Template / seed predictability** — Default: **SHA256-mix** chain seed before template `random.Random` (`expand_seed_for_problem_rng` in `lemma/problems/generated.py`); ids stay `gen/<seed>`. **Public** seed→theorem map remains deterministic (precompute still possible). Rollback: **`LEMMA_GENERATED_LEGACY_PLAIN_RNG=1`**. Boundary, builder promotion, and release checklist: [problem-supply-policy.md](problem-supply-policy.md).
- [x] **`LEMMA_PROBLEM_SOURCE=frozen` (miniF2F)** — Fail-closed unless **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (`get_problem_source`, direct frozen-id `resolve_problem`, `validator-check`).
- [x] **Toolchain / image pins** — Lean and Mathlib pins remain release inputs; local `lemma/lean-sandbox:latest` is dev-only. Production operators publish an immutable sandbox ref and set `LEAN_SANDBOX_IMAGE` consistently. See [toolchain-image-policy.md](toolchain-image-policy.md).

### Validator protocol & fairness

- [x] **`deadline_block` enforcement** — Validator drops responses when chain head ≥ synapse `deadline_block` after the forward returns.
- [x] **Cross-validator problem alignment** — **`LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS`** subtracts from RPC head before seed + forward deadline (`effective_chain_head_for_problem_seed`); CLI/status/rehearsal paths aligned. See [catalog-sources.md](catalog-sources.md).
- [x] **Workspace cache key** — Optional **`LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH=1`**: cache slot includes truncated SHA256 of `Submission.lean` (`workspace_verify_cache_key` in `lemma/lean/workspace.py`). Default off (template-only key; faster reuse).

### Trust & sybil

- [x] **Sybil economics** — Operator guide [sybil_economics.md](sybil_economics.md): Lemma dedup vs coldkey sybil realities, UID pressure, offline replay helper, the decision gate required before sybil/Pareto reward changes, the decision-record template, and the policy rubric for interpreting replay results. The replay analyzer now supports `--require-decision-ready` plus concrete `decision_data_gaps` for release checklists. **Still open:** run the replay on real private exports and make a governance decision before reward-code changes; tie-break / stake policy remains subnet governance ([`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml)).
- [x] **Judge / infra trust** — HTTP peer check for **`judge_profile_sha256`** ships (`LEMMA_JUDGE_PROFILE_ATTEST_*`) and is documented as operator coordination, not Byzantine consensus or transport security. Stronger attestations (e.g. signed/on-chain or k-of-n governance) remain a separate design. See [judge-profile-attest.md](judge-profile-attest.md).

### Compute placement

- [x] **Validator Lean load** — [validator_lean_load.md](validator_lean_load.md): concurrency caps, **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** trust vs CPU, remote verify worker; aligns with [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) `compute_distribution`.
- [x] **Reference miner boundary** — [miner.md](miner.md): bundled miner is a minimal Axon compatibility path, not the place for competitive solver strategy, broad operator UX, or container-execution redesign.

### Transport (long-term)

- [x] **Axon/Dendrite** — [transport.md](transport.md): current Dendrite/synapse + body-hash integrity; relation to `knowledge/subnet.invariants.yaml` deprecation for **new** designs vs Lemma’s shipping stack; HTTP + Epistula recorded as a major-release migration gate, not a second default transport.

### Judge input robustness

- [x] **Trace/Judge parsing** — `parse_rubric_json` prefers brace-balanced spans that open like `{"coherence"|"exploration"|"clarity"` before naive first-`{` slicing; invalid dict-shaped candidates are skipped so a later valid rubric object can win; repeated valid rubric occurrences, even identical echoes, fail closed. Miner text is fenced and triple-backtick escapes are broken before judge calls. Determined injection remains model-strength dependent.

### Optional protocol hooks

- [x] **Miner verify attest** — Optional path has v2 validator-hotkey-bound signatures, salted spot full-verify selection, no credibility gain for attest-trusted skips, challenge-field binding before scoring, and an explicit non-TEE threat model. See [miner-verify-attest.md](miner-verify-attest.md).
- [x] **Commit-reveal** — Usable optional path has bounded validator-keyed miner cache, shared hex normalization, reveal preimage checks, and an explicit threat model. See [commit-reveal.md](commit-reveal.md).

---

## Plumbing / cleanup (lower urgency than mechanism gaps)

Track in issues or refactors as capacity allows: remaining human-friendly CLI wrappers and other small runtime glue. Recent cleanup removed `validator/query.py`, split catalog dev helpers out of runtime, merged validator startup gates shared by `validator-check` and `service`, collapsed warm Lake-cache behavior to the single `LEMMA_LEAN_ALWAYS_CACHE_GET` override, inlined trace-length scoring, removed single-use miner/validator helpers, dropped an unused strict-judge assertion wrapper, removed an unused problem-seed boundary-label helper, moved theorem status/problem inspection, one-shot judge preview, and validator config summary to `lemma-cli`, and trimmed `lemma meta` to concise hashes by default.

---

## References

- Non-overlapping cleanup and repo-split plan: [workplan.md](workplan.md)
- Full external-audit remediation checklist (prioritized): [audit-remediation.md](audit-remediation.md)
- Toolchain and image pinning: [toolchain-image-policy.md](toolchain-image-policy.md)
- Problem supply policy: [problem-supply-policy.md](problem-supply-policy.md)
- Implementation map: [incentive_migration.md](incentive_migration.md)
- Objective decision: [objective-decision.md](objective-decision.md)
- Proof intrinsic scoring decision: [proof-intrinsic-decision.md](proof-intrinsic-decision.md)
- Judge incentive decision: [judge-incentive-decision.md](judge-incentive-decision.md)
- Credibility exponent decision: [credibility-exponent-decision.md](credibility-exponent-decision.md)
- Commit-reveal threat model: [commit-reveal.md](commit-reveal.md)
- Miner verify attest threat model: [miner-verify-attest.md](miner-verify-attest.md)
- Judge profile peer attest threat model: [judge-profile-attest.md](judge-profile-attest.md)
- Scoring entrypoint: `lemma/scoring/rewards.py`, `lemma/scoring/proof_intrinsic.py`
- Epoch loop: `lemma/validator/epoch.py`
