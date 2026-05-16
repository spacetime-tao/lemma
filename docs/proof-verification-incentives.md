# Proof Verification Incentives

Lemma's reward axis is formal proof validity: miners earn for producing
Lean-valid proofs for published theorem statements.

## Design Objective

One sentence:

> Lemma rewards Lean-valid proofs for published theorem statements.

This keeps the subnet objective close to the thing validators can reproduce:
given a locked theorem statement and a submitted `Submission.lean`, Lean either
accepts the proof or rejects it.

## Reward Shape

1. **Eligibility:** the submitted proof must pass the pinned Lean toolchain,
   Mathlib revision, sandbox policy, theorem binding checks, and cheat scans.
2. **Proof event:** each eligible miner entry records a positive binary event.
   Invalid, missing, late, or mismatched responses record a negative event when
   the validator successfully queried that UID.
3. **Verifier reuse:** validators may reuse a Lean result for identical proof
   payloads inside one epoch, but that does not remove a miner from rewards.
4. **Rolling weights:** per-UID rolling scores are updated by pass/fail events.
   Passes and misses are asymmetric: harder splits lift the rolling score more,
   while easier misses decay it more. Positive rolling scores become normalized
   miner weights; same-coldkey hotkeys share one coldkey allocation instead of
   multiplying it.

## Current Live Rollout

The live validator path is intentionally simple: a submitted proof either passes
Lean verification for the published theorem and enters scoring, or it does not.

That binary gate is separate from final allocation. A Lean-valid proof moves the
miner score upward; an ordinary miss or Lean failure moves it downward. Harder
proofs move scores up faster; easier misses move scores down faster because an
easy miss is more informative than a hard miss. The move is smoothed over time,
so one miss should not erase a strong recent history. Verifier-local
infrastructure failures are excluded from the score update for that UID.

By default, all queried UIDs share one theorem. `LEMMA_UID_VARIANT_PROBLEMS=1`
is an opt-in anti-Sybil mode where each queried UID receives a deterministic
same-split variant. This does not prove human identity; it makes extra accounts
require extra proof work.

## Out Of Scope For Rewards

- Rewriting the theorem in an easier form.
- Comment or whitespace padding.
- Proof scripts that pass only by adding unsound assumptions.
- Extra syntax that does not improve the checked proof.

## Cadence Implications

Proof-verification scoring keeps the hot path focused on the verifier. Miner
responses can be small because a proof script is enough for scoring.

That makes 50-block or 25-block theorem windows more plausible, but Lean
verification remains the hard budget. Shorter windows should be adopted only
after warm-cache verification, remote worker throughput, and miner response time
fit the target cadence.

For the current generated lane, 25 blocks is a reasonable target only if the
operator can keep verifier caches warm and bound miner response time. Cold-cache
verification can still consume most of a 5-minute window.

## Implementation Sequence

1. Keep proof-verification reward assembly pinned by tests. **Done.**
2. Keep the live miner payload centered on `proof_script`. **Done.**
3. Keep validator readiness tied to the verifier and subnet pins. **Done.**

## Decision Log

| Date | Decision |
| --- | --- |
| 2026-05 | Live rewards should be proof-only: Lean-valid proofs become reward-eligible; invalid proofs cannot receive miner rewards. |
| 2026-05 | Chain weights should use difficulty-weighted rolling proof scores, not only the latest passed set. |
