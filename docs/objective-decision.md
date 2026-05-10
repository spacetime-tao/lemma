# Objective Decision

This note pins the current one-sentence objective so the mechanism does not drift
into rewarding whatever the latest scoring layer happens to measure.

## One-Sentence Objective

Lemma incentivizes miners to produce Lean-valid mathematical proofs for
published theorem statements.

## Current Incentive Layer

The live scoring path has a second layer after Lean passes: a pinned LLM judge
scores the miner's informal reasoning trace. That judge layer is useful for
bootstrapping readable reasoning traces and training data, but it is not the
core objective by default.

Plainly:

- **Core objective:** produce a proof that Lean accepts for the stated theorem.
- **Current bootstrap ranking signal:** among Lean-valid submissions, reward
  clearer informal reasoning using the shared judge profile.
- **Governance choice:** if explanation quality becomes permanent, say so
  explicitly and update this objective.

## Why This Matters

Lean verification is objective and reproducible. LLM judging is useful but
subjective. Keeping those roles separate prevents the subnet from accidentally
becoming a prose-optimization game while still allowing the current judge layer
to help during bootstrapping.

## Change Gate

Any future scoring change should answer this first:

> Does this make Lean-valid theorem proving easier to measure, harder to game,
> or more economically useful?

If the answer is no, the change should not be part of the core incentive path.
See [judge-incentive-decision.md](judge-incentive-decision.md) and
[proof-intrinsic-decision.md](proof-intrinsic-decision.md) for the two current
scoring decision gates.
