# Proof Intrinsic Metric Decision

This note keeps `proof_intrinsic_score` from becoming a second reward system.

Treat every scoring line as a liability. If a signal is weak, do not add more
guards around it. Fix the incentive or keep the signal out of live rewards.

## Current Boundary

Live validator scoring does not call `proof_intrinsic_score`.

The function is research-only. It strips Lean comments, then scores proof text
length, `by` frequency, and non-empty line count.

Live rewards are proof-only. A proof must pass Lean for the published theorem
before it can receive score. See
[proof-verification-incentives.md](proof-verification-incentives.md).

## Problem

The heuristic is not mathematical value.

It can reward:

- long strings;
- long names;
- repeated trivial `have` blocks;
- extra lines;
- syntax bulk.

Comment stripping fixed the easiest padding path. It did not make the score a
proof-quality metric.

## Decision

Keep Lean verification as the live floor.

Keep `proof_intrinsic_score` out of the live default path.

Do not add more regex padding detectors as the main fix. If Lemma studies proof
shape, prefer Lean-backed or elaborator-backed measurements.

## Allowed Next Work

- Keep focused tests for the current research heuristic.
- Prototype Lean-backed metrics outside live scoring.
- Keep reward tests pinned to proof-verification behavior.

## Offline Metric Gate

An offline metric is worth keeping only if it is:

- deterministic across validators;
- cheap enough for explicit export or shadow runs;
- harder to pad than proof text length;
- tested against honest proofs and padding attempts.

Do not promote a metric from offline analysis without real export data.

Minimum review data:

1. A private `full` validator export with `LEMMA_LEAN_PROOF_METRICS=1`.
2. Several theorem ids with multiple successful submissions from multiple UIDs.
3. One consistent `judge_profile_sha256`.
4. Analyzer output from `tools.proof_metrics_analyze`.
5. Padding fixtures: comments, strings, unused trivial `have`, long names, and
   extra lines.

The gate fails if the metric mostly tracks proof length, rewards obvious
padding, often fails to probe, or adds too much runtime cost.

## Decision Choices

After the export clears `--require-decision-ready`, choose exactly one:

| Choice | Meaning |
| --- | --- |
| Keep offline | Keep a Lean-backed metric in private/offline reports only. |
| Collect more data | Evidence is inconclusive. |
| Reduce or remove | The text metric mostly rewards bulk or padding. |
| No decision | The export is not ready for review. |

No choice here makes a metric a live reward input.

## Analyzer Lines To Preserve

When writing a public decision note, keep the private JSONL private. Quote only
summary lines such as:

- row counts and failed probe counts;
- `decision_data_blockers`, `decision_data_gaps`, and `decision_ready`;
- `export_context`;
- `gate_verdict` and `gate_reasons`;
- within-theorem correlations;
- padding outliers;
- same-theorem disagreement examples.

Decision template:

```text
Proof intrinsic metric decision:
Chosen policy: keep offline | collect more data | reduce/remove | no decision
Decision ready: yes | no
Reason:

Evidence reviewed:
- Export dataset:
- Analyzer command:
- Export profile:
- Row counts:
- Blockers and gaps:
- Export context:
- Gate verdict:
- Within-theorem correlations:
- Padding/outlier notes:
- Human review notes:

Metric changes:
- proof_intrinsic_score changes:
- Replacement metric, if any:
- Migration notes:

Rollback:
- Env/config rollback:
- Operator notice:
- Follow-up review date:
```

## Prototype Boundary

Do not wire a new proof-side metric into live scoring.

The current prototype is opt-in:

```text
LEMMA_LEAN_PROOF_METRICS=1
```

After a proof passes Lean, the probe asks Lean to `#print` the verified
`Submission.<theorem>` declaration with `pp.all`. It records:

- byte count;
- line count;
- delimiter count;
- max delimiter depth;
- probe exit code.

Rewards and weights ignore this field.

When `LEMMA_TRAINING_EXPORT_JSONL` is set, the `full` profile can include
`proof_metrics`. The `summary` profile omits it.

Use:

```bash
uv run python -m tools.proof_metrics_analyze <train.jsonl>
```

`--require-decision-ready` exits nonzero until the export is ready for human
review. Passing that flag still does not approve a scoring change.

## Credibility Boundary

Verify credibility asks one narrow question: does this UID keep submitting
proofs that pass validator Lean verification?

It is not a padding detector. A Lean-valid padded proof can still improve
credibility. Study padding in offline proof-metric analysis, not in reputation
credibility.

## Calibration Notes

On 2026-05-09, a controlled Docker run tested several proofs of:

```lean
two_plus_two_eq_four : (2 : Nat) + 2 = 4
```

Findings:

- `rfl` was the small baseline.
- `norm_num` printed a larger proof term.
- A real structured `have` proof raised metrics.
- Comment padding no longer raises the normalized text heuristic.
- String padding can raise byte metrics.
- Unused trivial `have` padding can still fool the text heuristic.
- Delimiter count looked more useful than raw bytes in the tiny sample, but it
  is still research-only.

The analyzer still reported `gate_verdict=research_only`.

Avoid these as live scoring inputs:

- wall-clock build time;
- raw proof text length;
- axiom count by itself.

## Open Questions

- Which Lean-backed signals help offline proof-metric research?
- Which informal proof explanations should be reviewed outside the live
  protocol?
- Should hard theorem supply and bounty curation be the long-term path instead
  of guessing proof difficulty from one submitted proof?
