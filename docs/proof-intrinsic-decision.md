# Proof Intrinsic Scoring Decision

This note keeps `proof_intrinsic_score` from quietly growing into a second,
regex-shaped judge. Treat every line of scoring code as a liability: if the
signal is weak, do not patch it with more small guards unless the underlying
incentive becomes clearer.

## Current Behavior

Validator scoring only reaches this layer after a proof passes Lean verification.
The final score blends two signals:

1. `proof_intrinsic_score`, controlled by `LEMMA_SCORE_PROOF_WEIGHT`.
2. The judged informal reasoning rubric.

The default is `LEMMA_SCORE_PROOF_WEIGHT=0.10`, meaning the heuristic contributes
10 percent of the blend and the judge contributes 90 percent. The heuristic is
deterministic and local: it strips Lean comments by default, then scores proof
text length, `by` frequency, and line count.

## Problem

The heuristic is not a measure of mathematical value. It can still reward syntax
bulk more than proof quality:

- Long string literals and long names can inflate length.
- Trivial scaffolding like repeated `have ... by trivial` can inflate structure.
- Extra lines can increase the score without making the theorem harder.
- Comment stripping removed the easiest padding path, but it did not solve the
  general problem.

Removing the heuristic without another decision would make the judge even more
dominant. Raising the heuristic weight would reward padding. Both are bad default
moves.

## Decision

Keep Lean pass/fail as the objective floor.

Keep the current proof intrinsic heuristic only as a low-weight bootstrap signal.
Do not raise its default weight. Do not add more regex padding detectors as the
main fix. If the subnet needs a stronger proof-side score, it should come from a
Lean-backed or elaborator-backed signal, not from more text-shape guesses.

The judge should also be treated as a bootstrap signal unless the project makes
an explicit product decision that informal reasoning quality is permanently part
of the incentive mechanism.

## Acceptable Next Code Changes

1. Keep `LEMMA_SCORE_PROOF_WEIGHT` low by default unless a stronger proof-side
   signal replaces the current text heuristic.
2. Add focused tests that preserve the current heuristic behavior while the
   migration is planned, so accidental scoring drift is visible.
3. Prototype a replacement metric outside the live default path, using signals
   that Lean or its elaborator can justify.
4. Make any scoring-default change in a separate commit with docs and migration
   notes, not hidden inside a cleanup patch.

## Replacement Metric Gate

A replacement for `proof_intrinsic_score` should be accepted only if it is:

- Deterministic across validators.
- Cheap enough for validator load.
- Harder to pad than proof text length.
- Covered by tests with honest short proofs, honest longer proofs, and padding
  attempts.
- Reflected in `judge_profile_sha256` or another scoring/profile pin when it
  affects consensus-critical validator behavior.

Possible research directions include proof term size, elaborator trace summaries,
nontrivial goal transitions, tactic trace structure, and imported theorem usage.
These are starting points, not approved designs.

## Prototype Boundary

Do not wire a new proof-side metric into live scoring until it passes the gate
above. The first prototype is outside the default validator scoring path and
writes measurements for comparison only.

Good prototype shape:

- Reuse the existing verified workspace after Lean pass.
- Add one extra Lean probe file only in the prototype path.
- Record candidate metrics beside the current score so they can be compared on
  real submissions before any default changes.
- Keep `entry_from_scores` behavior pinned by tests while the replacement is
  evaluated.

Current prototype: set `LEMMA_LEAN_PROOF_METRICS=1` to attach compare-only
`proof_metrics` to `VerifyResult`. The probe asks Lean to `#print` the verified
`Submission.<theorem>` declaration with `pp.all` enabled, then records only the
printed byte count, line count, and probe exit code. Rewards and weights ignore
this field.

The opt-in Docker and host Lean golden tests assert that the probe returns
metrics on a real passing proof when those suites are enabled.

When `LEMMA_TRAINING_EXPORT_JSONL` is set, the `full` export profile includes
`proof_metrics` for successfully judged rows. `reasoning_only` intentionally
omits it because the field is proof-derived research data.

Signals to avoid as scoring inputs:

- Wall-clock build time, because it depends on hardware, cache warmth, and Docker
  placement.
- Raw proof text length, because that is the current weak proxy.
- Axiom count by itself, because legitimate math can require allowed classical
  axioms.

## Open Questions

- What Lean-backed signal should eventually replace the text heuristic?
- Is informal reasoning a permanent incentive target, or only a bootstrap aid?
- Should hard theorem supply and bounty-style curation become the stronger long
  term path instead of trying to infer proof difficulty from one submitted proof?
