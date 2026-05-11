# Objective Decision

This note pins the reward objective.

## Objective

Lemma rewards Lean-valid proofs for published theorem statements.

## Incentive Boundary

The live reward path is proof-only:

- Lean accepts the proof for the locked theorem: it can enter scoring.
- Lean rejects the proof: it cannot receive proof score.

Informal reasoning can help humans and datasets. It is not a live reward axis.

## Why This Matters

Lean verification is objective and reproducible.

The live game stays simple:

1. publish work;
2. verify work mechanically;
3. pay for valid work.

## Boundary Check

Every reward change should answer yes to at least one question:

- Does this make Lean-valid theorem proving easier to measure?
- Does this make it harder to game?
- Does this make the work more useful?

If not, keep it out of the core reward path.

Related:

- [proof-verification-incentives.md](proof-verification-incentives.md)
- [proof-intrinsic-decision.md](proof-intrinsic-decision.md)
