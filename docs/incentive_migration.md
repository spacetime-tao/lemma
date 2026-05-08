# Incentive layer hard-migration

This document tracks **post-audit** mechanism changes in Lemma: proof-centric scoring, deduplication, EMA reputation, expanded templates, and reserved protocol hooks.

## Implemented (defaults)

| Mechanism | Env / behavior |
|-----------|----------------|
| Proof + judge blend | `LEMMA_SCORE_PROOF_WEIGHT` (default **0.65**); judge gets **1 − weight**. |
| Identical submission dedup | `LEMMA_SCORING_DEDUP_IDENTICAL=1` — same `(theorem, proof, trace)` keeps best score. |
| Coldkey dedup | `LEMMA_SCORING_COLDKEY_DEDUP=1` — one hotkey per coldkey (metagraph). |
| EMA reputation | `LEMMA_REPUTATION_EMA_ALPHA` (default **0.08**); state file `LEMMA_REPUTATION_STATE_PATH` or `~/.lemma/validator_reputation.json`. |
| Multi-theorem epochs | `LEMMA_EPOCH_PROBLEM_COUNT` (default **1**) — sequential challenges per epoch. |
| Judge hardening | Fenced miner blocks + strict single-object JSON rubric parse. |
| Empty-epoch uniform | Validator UID excluded from uniform weights when possible. |

## Reserved flags (not implemented)

These fail validator startup if set to `1`:

- `LEMMA_COMMIT_REVEAL_ENABLED` — two-phase commit / reveal for proofs (anti copy-pool gossip).
- `LEMMA_MINER_VERIFY_ATTEST_ENABLED` — miners submit signed Lean verify artifacts; validators spot-check.
- `LEMMA_JUDGE_PROFILE_ATTEST_ENABLED` — cross-validator agreement on judge profile hash (on-chain or quorum).

Implementations should extend the synapse / signing path and add explicit tests before enabling defaults.

## Generated registry

Adding templates changes `generated_registry_sha256`. Operators must run `lemma configure subnet-pins` (or update `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`) after upgrading.

## References

- Scoring: `lemma/scoring/rewards.py`, `lemma/scoring/proof_intrinsic.py`, `lemma/validator/epoch.py`
- Dedup: `lemma/scoring/dedup.py`
- Reputation: `lemma/scoring/reputation.py`
- Problem mix: `lemma/problems/generated.py`, `lemma/common/problem_seed.py` (`mix_sub_problem_seed`)
