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
text length, `by` frequency, and non-empty line count.

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

## Go/No-Go Validation Gate

Do not change live rewards from this research path until the decision is backed
by real export data and adversarial fixtures.

Minimum gate for the next scoring decision:

1. Collect a real validator `full` export with `LEMMA_LEAN_PROOF_METRICS=1`.
   Use only rows where the proof-metric probe exits successfully.
2. Run `tools.proof_metrics_analyze` and keep the report with the decision
   notes. Failed probe rows are a reliability signal, not scoring evidence.
3. Compare the candidate metric against honest short proofs, honest longer
   proofs, and padding attempts: comments, long string literals, unused trivial
   `have` blocks, long names, and extra lines.
4. Make one explicit choice in a separate commit:
   - **replace** `proof_intrinsic_score` with a Lean-backed metric,
   - **keep** the current low-weight heuristic while collecting more data, or
   - **remove/reduce** the proof-text component if no candidate clears the gate.

The gate fails if the candidate mostly tracks raw proof text length, rewards
obvious Lean-valid padding, has frequent probe failures, or adds enough runtime
cost to make validator operation worse.

The synthetic fixture at `tests/fixtures/proof_metrics_validation.jsonl` exists
only to keep the analyzer honest around this gate: successful padding-like rows
should be visible as outliers, while failed probe rows should be counted but not
used as calibration evidence. It is not a substitute for real validator export
data.

Any accepted scoring change must update tests, operator docs, migration notes,
and the validator scoring/profile pin. It must not be hidden inside cleanup.

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

Use `uv run python -m tools.proof_metrics_analyze <train.jsonl>` to compare
exported proof metrics against proof text length, current `proof_intrinsic_score`,
and judge composite before considering any scoring change. The analyzer counts
failed proof-metric probes separately and excludes them from correlations and
padding-outlier lists; failed probe output is not proof-term evidence.

## Credibility Boundary

Verify credibility is intentionally not a padding detector. It answers a narrower
question: does this UID keep submitting proofs that pass validator Lean
verification?

That means a Lean-valid but padded proof can still improve credibility. Do not
fix that by adding text-shape penalties to the credibility EMA. Padding belongs
in the proof-side scoring decision above, where any replacement signal can be
measured, profiled, and pinned before it affects rewards.

The compare-only proof metrics export is the current place to study that
orthogonal signal. If those metrics become reliable enough to score, wire them
through the proof-side gate, not through reputation credibility.

## Initial Calibration

On 2026-05-09, a controlled Docker calibration ran five proofs of the same small
theorem, `two_plus_two_eq_four : (2 : Nat) + 2 = 4`, with
`LEMMA_LEAN_PROOF_METRICS=1`. The run used real Lean verification, then analyzed
the exported rows with `tools.proof_metrics_analyze`.

| Proof shape | Proof chars | Lean metric bytes | Lean metric lines | Current `proof_intrinsic_score` | Note |
| --- | ---: | ---: | ---: | ---: | --- |
| `rfl` | 115 | 538 | 9 | 0.3159 | Small baseline. |
| `norm_num` | 120 | 2129 | 32 | 0.3182 | Larger printed proof term than `rfl`. |
| Structured `have` proof | 214 | 2526 | 40 | 0.4256 | Metric rises with real proof structure. |
| Comment padding + `norm_num` | 4190 | 2129 | 32 | 0.5217 | Historical run: Lean metric matched `norm_num`; the text heuristic still rose because stripped comment lines left line-count bulk. |
| String padding + `norm_num` | 2150 | 4160 | 34 | 0.4760 | Lean metric also rises; the probe is not padding-proof. |

Analyzer summary:

```text
rows_total=5
rows_with_proof_metrics=5
metric_bytes: n=5 min=538 median=2129.0 mean=2296.4 max=4160
proof_len_chars: n=5 min=115 median=214.0 mean=1357.8 max=4190
corr(metric_bytes, proof_len_chars)=0.3358
corr(metric_bytes, proof_intrinsic)=0.6028
```

Interpretation: the Lean probe is useful as a research signal because it ignores
pure comment padding in this sample. It is not sufficient as a scoring signal:
valid but useless term-level padding, such as an unused large string, can still
inflate it. Keep it compare-only until a better Lean/elaborator-backed metric is
defined and tested against more padding attempts.

Follow-up: the historical run above exposed one direct bug in the current
heuristic. Comment-only and blank lines are now normalized out before line count,
so comment padding no longer receives leftover line-count credit. This is a
normalization fix, not a broader proof-quality metric.

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
