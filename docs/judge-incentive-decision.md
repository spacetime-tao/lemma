# Optional Prose Evaluation Boundary

Lemma's reward objective is proof-only: a submitted Lean proof must pass the
pinned verifier, then deterministic proof-side signals rank the passing proofs.
See [proof-only-incentives.md](proof-only-incentives.md).

Prose evaluation can still be useful outside rewards:

- debugging why a prover tried a particular proof path;
- building private training exports;
- helping humans review difficult examples;
- comparing model behavior during research.

Those uses should remain out of the permanent validator reward function unless a
future governance decision explicitly changes the objective. New code should not
add reward-critical dependence on explanation quality, rubric-shaped text, or a
specific inference provider.

## Boundary

Reward-critical:

1. theorem binding and protocol checks;
2. Lean verification result;
3. deterministic proof-side scoring;
4. validator profile pins for cadence, verifier, scoring, and registry state.

Optional / research:

1. informal reasoning text;
2. prose labels;
3. explanation-quality reports;
4. private datasets for prover improvement.

This keeps the live economic signal tied to formal proof artifacts while still
allowing humans and models to learn from explanations.
