# Binary Proof-Pass Reward Boundary

Lemma's live reward objective is binary Lean pass/fail: a submitted proof either
passes the pinned verifier for the published theorem, or it does not. See
[proof-only-incentives.md](proof-only-incentives.md).

## Live Reward Path

Reward-critical:

1. theorem binding and protocol checks;
2. pinned Lean verification result;
3. binary proof-pass scoring;
4. validator profile pins for cadence, verifier, scoring, and registry state.

## Local Research Surface

Local prose evaluation can still help humans inspect examples, debug prover
behavior, or build private research exports. It does not produce subnet weights
or miner HTTP scores.

Research-only:

1. informal reasoning text;
2. prose labels;
3. explanation-quality reports;
4. private datasets for prover improvement.
