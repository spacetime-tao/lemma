# Incentive layer hard-migration

This document tracks **post-audit** mechanism changes in Lemma: proof-centric scoring, deduplication, EMA reputation, expanded templates, and reserved protocol hooks.

**Checklist (done vs open):** [incentive-roadmap.md](incentive-roadmap.md).

## Implemented (defaults)

| Mechanism | Env / behavior |
|-----------|----------------|
| Proof + judge blend | `LEMMA_SCORE_PROOF_WEIGHT` (default **0.35** intrinsic / **0.65** judge composite); tune per subnet policy. |
| Identical submission dedup | `LEMMA_SCORING_DEDUP_IDENTICAL=1` — same `(theorem, proof, trace)` keeps best score. |
| Coldkey dedup | `LEMMA_SCORING_COLDKEY_DEDUP=1` — one hotkey per coldkey (metagraph). |
| EMA reputation | `LEMMA_REPUTATION_EMA_ALPHA` (default **0.08**); state file `LEMMA_REPUTATION_STATE_PATH` or `~/.lemma/validator_reputation.json`. |
| Verify credibility | `LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA` (default **0.08**) — EMA toward 1.0 on Lean verify pass, 0.0 on fail; persisted with reputation JSON. Applied as `(credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)` after EMA smoothing (exponent **0** disables the multiplier). |
| Proof intrinsic | `LEMMA_SCORE_PROOF_WEIGHT` blend; `LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS` (default **on**) strips Lean `--` / `/- … -/` before the length/`by`-count heuristic. |
| Multi-theorem epochs | `LEMMA_EPOCH_PROBLEM_COUNT` (default **1**) — sequential challenges per epoch. |
| Judge hardening | Fenced miner blocks + strict single-object JSON rubric parse. |
| Empty-epoch uniform | Validator UID excluded from uniform weights when possible. |
| Response deadline | After each forward, responses with `deadline_block` set are dropped if chain head is already at or past that block (late HTTP completions are not scored). |
| Frozen miniF2F catalog | `LEMMA_PROBLEM_SOURCE=frozen` requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (fail-closed otherwise). |

## Reserved flags (not implemented)

These fail validator startup if set to `1`:

- `LEMMA_COMMIT_REVEAL_ENABLED` — two-phase commit / reveal for proofs (anti copy-pool gossip).
- `LEMMA_MINER_VERIFY_ATTEST_ENABLED` — miners submit signed Lean verify artifacts; validators spot-check.
- `LEMMA_JUDGE_PROFILE_ATTEST_ENABLED` — cross-validator agreement on judge profile hash (on-chain or quorum).

Implementations should extend the synapse / signing path and add explicit tests before enabling defaults.

**Planned order (see [incentive-roadmap.md](incentive-roadmap.md)):** miner-side verify attestation first (cuts validator Lean load when paired with spot-checks), then commit–reveal and judge-profile quorum / chain hooks as designed.

## Generated registry

Adding templates changes `generated_registry_sha256`. Operators must run `lemma configure subnet-pins` (or update `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`) after upgrading.

## References

- Scoring: `lemma/scoring/rewards.py`, `lemma/scoring/proof_intrinsic.py`, `lemma/validator/epoch.py`
- Dedup: `lemma/scoring/dedup.py`
- Reputation: `lemma/scoring/reputation.py`
- Problem mix: `lemma/problems/generated.py`, `lemma/common/problem_seed.py` (`mix_sub_problem_seed`)
