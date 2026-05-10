# Objective Decision

This note pins the current one-sentence objective so the mechanism does not drift
into rewarding whatever the latest scoring layer happens to measure.

## One-Sentence Objective

Lemma rewards Lean-valid proofs for published theorem statements.

## Incentive Boundary

The reward path should be proof-only:

- **Eligibility:** Lean accepts the submitted proof for the locked theorem.
- **Scoring:** an eligible proof receives a binary pass score; current live cost
  is `0`.
- **Out of band:** informal reasoning can help humans, datasets, and debugging,
  but it is not a reward axis.

See [proof-only-incentives.md](proof-only-incentives.md) for the concrete design.

## Why This Matters

Lean verification is objective and reproducible. Binary live scoring keeps the
v0 game simple: publish work, verify work mechanically, pay for valid work.

## Boundary Check

Every reward change should preserve this test:

> Does this make Lean-valid theorem proving easier to measure, harder to game,
> or more economically useful?

If the answer is no, the change should not be part of the core incentive path.
See [proof-only-incentives.md](proof-only-incentives.md) and
[proof-intrinsic-decision.md](proof-intrinsic-decision.md) for the scoring
design gates.
