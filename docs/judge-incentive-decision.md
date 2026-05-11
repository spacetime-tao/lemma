# Proof Verification Reward Boundary

Lemma's live reward objective is proof verification.

A submitted proof must pass the pinned Lean verifier for the published theorem
before it can receive score.

See [proof-verification-incentives.md](proof-verification-incentives.md).

## Live Reward Path

Reward-critical data:

1. theorem binding and protocol checks;
2. pinned Lean verification result;
3. proof-verification scoring;
4. validator profile pins.

## Research Surface

Local prose evaluation can help humans inspect examples, debug prover behavior,
or build private research exports.

It does not produce subnet weights.

Research-only data:

- informal reasoning text;
- prose labels;
- explanation-quality reports;
- private datasets for prover improvement.
