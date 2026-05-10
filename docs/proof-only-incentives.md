# Proof-Only Incentive Design

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
2. **Equivalence:** identical normalized proof payloads are grouped so duplicate
   submissions do not create extra proof work for validators.
3. **Proof score:** each eligible proof group receives the same score before
   dedup, reputation, and subnet weight policy are applied.
4. **Weights:** group-level weights are mapped back to eligible miners after
   coldkey / sybil policy is applied.

## Current Live Rollout

The live validator path is intentionally simple: a submitted proof either passes
Lean verification for the published theorem and enters scoring, or it does not.

## What Not To Reward

- Longer prose explanations.
- Rubric-shaped writing.
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
| 2026-05 | Live rewards should be proof-only: Lean-valid proofs can enter scoring; invalid proofs cannot. |
