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
2. **Proof score:** each eligible miner entry receives the same proof score
   before reputation and subnet weight policy are applied.
3. **Verifier reuse:** validators may reuse a Lean result for identical proof
   payloads inside one epoch, but that does not remove a miner from rewards.
4. **Weights:** eligible proof entries become miner weights.
   Reputation/credibility can adjust an entry. When several hotkeys share one
   coldkey, that coldkey's allocation is partitioned among those hotkeys instead
   of multiplied.

## Current Live Rollout

The live validator path is intentionally simple: a submitted proof either passes
Lean verification for the published theorem and enters scoring, or it does not.

That binary gate is separate from final allocation. A Lean-valid proof earns
eligibility with the same base proof score; reputation, verify credibility,
Pareto layering, and same-coldkey partitioning are downstream policy that can
change weights after eligibility.

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

For the current generated v0 lane, 25 blocks is a reasonable target only if the
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
