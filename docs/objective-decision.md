# Objective Decision

This note pins the current one-sentence objective so the mechanism does not drift
into rewarding whatever the latest scoring layer happens to measure.

## One-Sentence Objective

Lemma rewards Lean-valid proofs for published theorem statements.

## Incentive Boundary

The reward path should be proof-only:

- **Eligibility:** Lean accepts the submitted proof for the locked theorem.
- **Scoring:** an eligible proof is a positive binary event; an ordinary miss or
  Lean failure is a negative event.
- **Allocation policy:** difficulty-weighted rolling history and same-coldkey
  partitioning can change final weights only after eligibility.
- **Out of band:** informal reasoning can help humans, datasets, and debugging,
  but it is not a reward axis.

See [proof-verification-incentives.md](proof-verification-incentives.md) for the concrete design.

## Why This Matters

Lean verification is objective and reproducible. The live scoring path stays
simple: publish work, verify work mechanically, pay for valid work.

## Boundary Check

Every reward change should preserve this test:

> Does this make Lean-valid theorem proving easier to measure, harder to game,
> or more economically useful?

If the answer is no, the change should not be part of the core incentive path.
See [proof-verification-incentives.md](proof-verification-incentives.md) and
[proof-intrinsic-decision.md](proof-intrinsic-decision.md) for the scoring
design gates.
