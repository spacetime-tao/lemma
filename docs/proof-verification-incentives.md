# Proof Verification Incentives

Lemma rewards Lean-valid proofs for published theorem statements.

That is the live reward axis.

## Reward Shape

1. The miner submits a proof script.
2. The proof must pass the pinned Lean toolchain, Mathlib revision, sandbox
   policy, theorem binding, and cheat scans.
3. Each eligible miner entry receives the same proof score before reputation and
   weight policy.
4. Validators may reuse one Lean result for identical proof payloads inside an
   epoch. This saves CPU. It does not remove a miner reward entry.
5. Reputation, Pareto weighting, and same-coldkey partitioning build final
   weights.

## Current Live Rule

Lean passes: the proof can enter scoring.

Lean fails: the proof cannot receive proof score.

## Out Of Scope For Rewards

These do not earn proof score:

- changing the theorem into an easier theorem;
- passing only by adding unsound assumptions;
- comment or whitespace padding;
- extra syntax that does not improve the checked proof;
- informal reasoning prose.

## Cadence

Proof-only scoring keeps miner responses small. Lean verification is still the
hard budget.

Shorter theorem windows should come only after measuring:

- warm-cache verify time;
- remote worker throughput;
- miner response time;
- live scored miner count.

## Implementation State

- Proof-verification reward tests exist.
- Live miner payload centers on `proof_script`.
- Validator readiness checks verifier and subnet pins.

## Decision Log

| Date | Decision |
| --- | --- |
| 2026-05 | Live rewards are proof-only: Lean-valid proofs can enter scoring; invalid proofs cannot. |
