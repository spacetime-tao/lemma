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
of the incentive mechanism. See [judge-incentive-decision.md](judge-incentive-decision.md).

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

1. Collect a real validator `full` export with `LEMMA_LEAN_PROOF_METRICS=1`
   ([training_export.md](training_export.md)). Use only rows where the
   proof-metric probe exits successfully. The export must include same-theorem
   comparisons: several theorem ids should have multiple judged successful
   submissions from multiple UIDs, otherwise metric size mostly measures theorem
   size rather than proof quality. Successful rows must also come from one
   consistent `judge_profile_sha256`; mixed validator profiles are not decision
   evidence.
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
should be visible as outliers or low-judge / high-metric candidates. It covers
comments, strings, unused trivial `have` blocks, and long names. Failed probe
rows should be counted but not used as calibration evidence. It is not a
substitute for real validator export data.

Any accepted scoring change must update tests, operator docs, migration notes,
and the validator scoring/profile pin. It must not be hidden inside cleanup.

## Decision Rubric

After a real export clears `--require-decision-ready`, make exactly one of these
choices. Treat this as a governance / scoring decision, not an analyzer result.

### Replace

Replace `proof_intrinsic_score` only if the candidate Lean-backed metric is
useful inside same-theorem comparisons:

- `corr_within_theorem(candidate, judge_composite)` is positive enough to matter
  across multiple theorem ids, not just globally correlated with theorem size.
- `same_theorem_metric_judge_disagreements(candidate)` is sparse and explainable
  under manual review.
- Padding fixtures and real rows do not show the candidate repeatedly rewarding
  comments, strings, unused trivial `have` blocks, long names, or extra lines.
- Runtime cost and probe failure rate are low enough for validator operations.
- The scoring/profile pin changes with the new reward input.

### Keep Low

Keep the current low-weight text heuristic when the evidence is inconclusive but
not actively harmful:

- Lean-backed candidates are noisy, saturated, or theorem-size dependent.
- Same-theorem disagreement examples exist but do not clearly favor padding.
- The current `proof_intrinsic_score` remains low-weight and does not dominate
  judge or Lean pass/fail behavior.
- More export data would plausibly change the conclusion.

### Reduce Or Remove

Reduce or remove the proof-text component when the evidence shows it is mostly a
liability:

- `same_theorem_metric_judge_disagreements(proof_intrinsic)` repeatedly shows
  the text heuristic preferring worse judged proofs.
- The heuristic mostly tracks proof length or syntactic bulk after comment
  stripping.
- No candidate Lean-backed metric clears the replacement gate.
- Keeping the heuristic would encourage miners to pad Lean-valid proofs.

### No Decision

Do not change scoring when the export fails readiness, lacks same-theorem
comparisons, lacks judge labels, has frequent probe failures, or depends on one
small hand-picked theorem family. In that case, collect more data or keep the
current low default.

## Analyzer Summary to Preserve

Keep the private JSONL export private. A public issue, PR, or governance note can
quote the analyzer summary lines and human review notes without publishing proof
scripts, traces, judge labels, or per-miner rows.

Copy these lines into the decision record:

| Line | Why it matters |
| --- | --- |
| `rows_total`, `rows_with_proof_metrics`, `rows_with_successful_proof_metrics`, `rows_with_failed_proof_metrics`, `invalid_json_lines` | Shows whether the export is complete enough and whether the Lean probe is reliable. |
| `decision_data`, `decision_data_blockers`, `decision_data_warnings`, `decision_data_gaps`, `decision_ready` | Separates "collect more data" from "ready for review." |
| `export_context` | Shows whether successful rows came from one judge profile and one generated registry. |
| `gate_verdict`, `gate_reasons` | Records the analyzer's conservative stop/go signal. |
| `corr_within_theorem(metric_bytes, judge_composite)`, `corr_within_theorem(metric_delimiters, judge_composite)`, `corr_within_theorem(proof_intrinsic, judge_composite)` | Measures proof-side signals inside same-theorem comparisons rather than mostly measuring theorem size. |
| `padding_outliers_by_proof_len_minus_metric_bytes`, `low_judge_high_metric_candidates` | Keeps obvious padding and low-judge / high-metric cases visible. |
| `same_theorem_metric_judge_disagreements(...)` | Lists examples that need human review before replacing, keeping, or reducing the heuristic. |

Decision-record template:

```text
Proof intrinsic scoring decision:
Chosen policy: replace | keep low | reduce/remove | no decision
Decision ready: yes | no
Reason:

Evidence reviewed:
- Export dataset:
- Analyzer command:
- Export profile:
- rows_total / rows_with_successful_proof_metrics / rows_with_failed_proof_metrics:
- decision_data_blockers:
- decision_data_gaps:
- export_context:
- gate_verdict / gate_reasons:
- within-theorem correlations:
- padding/outlier notes:
- same-theorem disagreement notes:
- Adversarial fixture notes:
- Human review notes:

Reward/profile changes:
- LEMMA_SCORE_PROOF_WEIGHT:
- proof_intrinsic_score changes:
- Replacement metric, if any:
- Profile pin fields:
- Migration notes:

Rollback:
- Env/config rollback:
- Operator notice:
- Follow-up review date:
```

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
`Submission.<theorem>` declaration with `pp.all` enabled, then records byte
count, line count, delimiter count, max delimiter depth, and probe exit code.
Rewards and weights ignore this field.

The opt-in Docker and host Lean golden tests assert that the probe returns
metrics on a real passing proof when those suites are enabled.

When `LEMMA_TRAINING_EXPORT_JSONL` is set, the `full` export profile includes
`proof_metrics` for successfully judged rows. `reasoning_only` intentionally
omits it because the field is proof-derived research data.

The operator checklist for collecting real proof-metrics rows lives in
[training_export.md](training_export.md). Keep those exports private.

Use `uv run python -m tools.proof_metrics_analyze <train.jsonl>` to compare
exported proof metrics against proof text length, current `proof_intrinsic_score`,
and judge composite before considering any scoring change. The analyzer counts
failed proof-metric probes separately and excludes them from correlations and
diagnostic candidate lists; failed probe output is not proof-term evidence. It
also reports low-judge / high-metric candidates so term-size inflation from
strings, unused trivial `have` blocks, or long names stays visible when the Lean
probe rises with the padding. Its `gate_verdict` is intentionally conservative:
`research_only` means do not wire the metric into rewards, `insufficient_data`
means collect a usable export first, and `manual_review_required` still does not
mean automatic approval. Its `decision_data_blockers` line is separate from the
metric verdict: blockers mean the export is too small or missing judge labels to
support a scoring decision, even if the metric gate itself has no obvious
padding finding. The readiness check also requires same-theorem comparison sets
so wide one-row-per-theorem exports cannot approve a proof-side scoring change.
For exports that include those comparison sets, `corr_within_theorem(...)`
subtracts each theorem's baseline before comparing metric movement to judge
movement; treat those lines as more relevant than global correlations when
judging whether a proof-side metric is measuring proof quality rather than
theorem size. The report also prints `same_theorem_metric_judge_disagreements`
for pairs where metric bytes, delimiter count, or the current text heuristic is
higher but the judge score is equal or lower; those examples should be
inspected before any replace / keep-low / remove decision.
`--require-decision-ready` is available for release checklists: it exits nonzero
unless the export clears readiness blockers and reaches the manual-review gate.
Passing that flag is not approval to change rewards; it only means there is
enough data to start the human decision. Modern exports include an
`export_context` block with non-secret profile and registry hashes; the analyzer
reports those counts and blocks decision readiness when successful rows mix judge
profiles or generated-registry hashes. It also prints `decision_data_gaps`,
which is the practical collection target list for the next export run.

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

V2 follow-up: on 2026-05-09, the same theorem was recalibrated with
`print_decl_pp_all_v2`, which records byte count, line count, delimiter count,
and max delimiter depth. The run used real Docker Lean verification with isolated
warm workspaces for each proof shape.

| Proof shape | Proof chars | Metric bytes | Metric lines | Delimiters | Max depth | Current `proof_intrinsic_score` | Note |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `rfl` | 115 | 698 | 11 | 35 | 4 | 0.3020 | Small baseline. |
| `norm_num` | 120 | 2289 | 34 | 128 | 8 | 0.3043 | Larger printed proof term than `rfl`. |
| Structured `have` proof | 167 | 2644 | 41 | 148 | 8 | 0.3606 | Delimiter count rose with a used intermediate proof. |
| Comment padding + `norm_num` | 7391 | 2289 | 34 | 128 | 8 | 0.3043 | Matches `norm_num`; comments no longer inflate the heuristic or Lean metrics. |
| String padding + `norm_num` | 1893 | 4072 | 36 | 128 | 8 | 0.4566 | Bytes rose, but delimiter shape stayed at `norm_num`. |
| Unused trivial `have` padding + `norm_num` | 225 | 2379 | 37 | 128 | 8 | 0.4534 | Lean metrics barely moved; text heuristic still rose. |
| Long-name padding + `norm_num` | 337 | 2505 | 37 | 128 | 8 | 0.3985 | Bytes rose modestly; delimiter shape stayed at `norm_num`. |

Analyzer summary:

```text
rows_total=7
rows_with_proof_metrics=7
rows_with_successful_proof_metrics=7
rows_with_failed_proof_metrics=0
gate_verdict=research_only
gate_reasons=padding_outliers
metric_bytes: n=7 min=698 median=2379.0 mean=2410.9 max=4072
metric_lines: n=7 min=11 median=36.0 mean=32.9 max=41
metric_delimiters: n=7 min=35 median=128.0 mean=117.6 max=148
metric_max_depth: n=7 min=4 median=8.0 mean=7.4 max=8
proof_len_chars: n=7 min=115 median=225.0 mean=1464.0 max=7391
corr(metric_bytes, proof_len_chars)=0.1322
corr(metric_bytes, proof_intrinsic)=0.6740
corr(metric_delimiters, proof_len_chars)=0.1659
corr(metric_delimiters, proof_intrinsic)=0.3917
```

Interpretation: delimiter count looks more useful than raw bytes for this small
sample because it ignores string padding, long-name padding, and unused trivial
`have` padding while still rising for the used structured proof. It is not yet a
reward signal: the sample is tiny, max depth saturates quickly, and the analyzer
still reports `research_only`. The next proof-side step should compare delimiter
shape on real validator exports before replacing, reducing, or removing the
current low-weight text heuristic.

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
