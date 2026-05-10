# Objective Decision

This note pins the current one-sentence objective so the mechanism does not drift
into rewarding whatever the latest scoring layer happens to measure.

## One-Sentence Objective

Lemma rewards valid, efficient Lean proofs for published theorem statements.

## Incentive Boundary

The permanent reward path should be proof-only:

- **Eligibility:** Lean accepts the submitted proof for the locked theorem.
- **Ranking:** deterministic proof-side efficiency signals compare passing
  proofs for the same challenge.
- **Out of band:** informal reasoning can help humans, datasets, and debugging,
  but it is not a permanent reward axis.

See [proof-only-incentives.md](proof-only-incentives.md) for the concrete design.

## Why This Matters

Lean verification is objective and reproducible. Proof-efficiency metrics are
not perfect, but they are at least tied to the formal artifact validators can
check. This keeps Lemma from becoming a prose-optimization game.

## Change Gate

Any future scoring change should answer this first:

> Does this make Lean-valid theorem proving easier to measure, harder to game,
> or more economically useful?

If the answer is no, the change should not be part of the core incentive path.
See [proof-only-incentives.md](proof-only-incentives.md) and
[proof-intrinsic-decision.md](proof-intrinsic-decision.md) for the scoring
design gates.
