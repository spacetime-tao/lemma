# Training export (validator JSONL)

Validators optionally append one JSON object per scored miner response each epoch when **`LEMMA_TRAINING_EXPORT_JSONL`** is set. Lemma **does not upload** files; operators rotate or ship logs themselves ([`scripts/training_export_upload_example.sh`](../scripts/training_export_upload_example.sh), [production.md](production.md)).

## Profiles (`LEMMA_TRAINING_EXPORT_PROFILE`)

| Profile | Schema | Contents | Use when |
| --- | --- | --- | --- |
| **`full`** (default) | `schema_version` **1** | `reasoning_*`, `theorem_statement`, `proof_script`, public `coldkey` when available from the metagraph, optional rubric/prose labels when enabled, optional `proof_metrics` when `LEMMA_LEAN_PROOF_METRICS=1`, non-secret `export_context` hashes, plus **`pareto_weight`** after weights are computed | Internal research, calibration, full offline replay |
| **`reasoning_only`** | `schema_version` **2** | Same reasoning fields + `block`, `theorem_id`, `uid`, `model_card`, non-secret `export_context` hashes; **no** proof text, **no** rubric, **no** `proof_metrics`, **no** `pareto_weight` | Sharing trace data with weaker direct incentive labels |

Set in `.env`:

```bash
LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/train.jsonl
LEMMA_TRAINING_EXPORT_PROFILE=reasoning_only
```

## Collect proof-metrics calibration data

Use this only for private validator research, not public dataset sharing. The
`full` profile includes proof text, optional labels, optional proof metrics, and
Pareto weights.

On a validator run where you want proof-side calibration rows:

```bash
LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/proof-metrics.jsonl
LEMMA_TRAINING_EXPORT_PROFILE=full
LEMMA_LEAN_PROOF_METRICS=1
```

Keep the normal production pins aligned (`LEAN_SANDBOX_IMAGE`,
timeouts, registry/profile hashes). `LEMMA_LEAN_PROOF_METRICS=1` adds one
compare-only Lean probe after a proof already passes verification; it does **not**
change rewards or weights.

Operator checklist:

1. Pick a private path for `LEMMA_TRAINING_EXPORT_JSONL`; do not commit or publish
   the export.
2. Run with `LEMMA_TRAINING_EXPORT_PROFILE=full` and
   `LEMMA_LEAN_PROOF_METRICS=1` long enough to collect varied successful proofs,
   including multiple successful submissions on the same theorem ids.
3. Keep a copy of the exact `.env` / validator settings used for the run.
   Exports now include non-secret `export_context` hashes (`lemma_version`,
   `judge_profile_sha256`, optional rubric/profile hashes,
   `generated_registry_sha256`), but those hashes are not a replacement for the
   full private run notes.
4. Run the analyzer below and save its text output beside the export.
5. Treat `gate_verdict=research_only` as a hard stop for live rewards.
   `manual_review_required` still means review, not approval.
6. Make any future scoring-default change in a separate commit with docs,
   migration notes, and the scoring/profile pin updated.

After collecting rows, run:

```bash
uv run python -m tools.proof_metrics_analyze /var/lib/lemma/proof-metrics.jsonl
```

Keep the analyzer report with any scoring decision notes. Look first at:

- `decision_data_blockers` and `decision_data_warnings`; blockers mean the
  export is not varied enough for a scoring decision yet,
- `decision_data_gaps`, which turns the blockers into concrete collection
  targets such as `successful_rows+44`, `comparison_theorems+3`, or
  `judge_profile_sha256_rows+6`,
- `export_context`, which should show one validator profile and one generated
  registry hash across successful rows,
- `rows_with_successful_proof_metrics` vs failed probe rows,
- correlations between metric bytes / delimiter-count shape data, proof text
  length, current `proof_intrinsic_score`, and any available quality labels,
- `within_theorem_comparisons` and `corr_within_theorem(...)`, which subtract
  each theorem's baseline before comparing proof metrics to quality labels,
- same-theorem disagreement candidates, which point to pairs where
  metric bytes, delimiter count, or the current text heuristic is higher but
  the quality label is equal or lower on the same theorem,
- padding-looking outliers and the conservative `gate_verdict`.

Do **not** change `LEMMA_SCORE_PROOF_WEIGHT` from one report alone. The proof-side
gate in [proof-intrinsic-decision.md](proof-intrinsic-decision.md) still requires
real export data plus adversarial padding fixtures before live reward changes.
Copy the analyzer summary lines, not the private JSONL, into that decision
record.

Analyze a local `full` export with proof metrics:

```bash
uv run python -m tools.proof_metrics_analyze /var/lib/lemma/train.jsonl
```

If the path is omitted, the tool reads `LEMMA_TRAINING_EXPORT_JSONL`. The
analyzer reports failed proof-metric probes separately and excludes them from
correlations/outlier lists, so calibration is based only on successful Lean
probe rows. It also reports minimum data-readiness blockers using conservative
defaults: at least 50 successful proof-metric rows, 5 theorem ids, 5 UIDs, and
quality labels. Successful rows must include one consistent
`judge_profile_sha256`; mixed validator profiles block a scoring decision, and mixed
generated-registry hashes do too. It also requires at least 3 theorem ids with 2
or more successful rows from 2 or more UIDs, so wide
one-row-per-theorem exports do not masquerade as proof-quality evidence. The
`decision_data_gaps` line is the shortest collection checklist for what remains
missing. The report then prints centered
within-theorem correlations for metric bytes, delimiter count, and the current
text heuristic against available quality labels, plus same-theorem disagreement
candidates for human review.

For release checklists, add `--require-decision-ready`. It exits nonzero unless
`decision_ready=yes`. This is only a readiness guard: it still requires manual
review and does not approve a scoring change.

The repo also keeps a synthetic analyzer fixture at
`tests/fixtures/proof_metrics_validation.jsonl`. It is useful for checking the
analysis code, but it is not evidence for a scoring change; use real validator
exports for that.

## Collect sybil/Pareto replay data

Use a private `full` export when evaluating sybil/Pareto reward changes. The
replay helper compares the current dedup/Pareto behavior against dedup-off
baselines and simulates exact-copy vs lightly rewritten K-miner pressure:

```bash
uv run python -m tools.sybil_replay_analyze /var/lib/lemma/train.jsonl
```

Current full exports include `theorem_statement` and public coldkeys when the
validator metagraph provides them. If older exports do not include coldkeys, the
coldkey replay assumes one coldkey per UID. That is still useful for
identical-copy and rewritten-copy pressure, but it is not evidence that coldkey
dedup is sybil resistance.

The report prints aggregate `summary_*` lines for exact-copy and rewritten-copy
clone pressure across the sampled epochs, then the per-epoch replay details.
The `decision_data_gaps` line is the shortest replay collection checklist, for
example `replayable_rows+47`, `epochs+4`, or `coldkey_rows+3`.
For release checklists, add `--require-decision-ready`. It exits nonzero unless
the export has enough clean rows, epochs, UIDs, theorem ids, and coldkey coverage
for a governance decision. Like the proof-metrics guard, this is not approval for
a reward change. Copy the summary lines, not the private JSONL, into the
decision record in [sybil_economics.md](sybil_economics.md).

## Gaming and leakage (why `reasoning_only` exists)

Exports are **not** a neutral “public good.” Depending on fields, they can teach models to:

- **Optimize labels instead of proofs** — rubric or label fields can expose scalar targets.
- **Copy proofs** — `proof_script` is a full solution for `theorem_id` at `block`.
- **Optimize incentives** — `pareto_weight` ties rows to the subnet weight map.
- **Reverse-engineer proof-side probes** — `proof_metrics` can expose candidate scoring research signals.

**`reasoning_only`** removes proof text, rubric/label scores, proof metrics, and Pareto weights. It **does not** remove all structure: `theorem_id`, `uid`, and `block` still support stratification or deanonymization risks if combined with other data. For maximum privacy, post-process or aggregate before publication.

## Schema reference

### `full` (`schema_version` 1)

- **`export_profile`**: `"full"`.
- **`export_context`**: non-secret provenance hashes for the validator run:
  `lemma_version`, `judge_profile_sha256`, optional rubric/profile hashes, and
  `generated_registry_sha256`.
- **`theorem_statement`**, **`proof_script`**, **`rubric`**: see [`training_export.py`](../lemma/validator/training_export.py).
- **`coldkey`**: public metagraph coldkey when available; omitted if unavailable.
- **`proof_metrics`**: optional compare-only Lean probe output when `LEMMA_LEAN_PROOF_METRICS=1`.
- After the epoch, **`pareto_weight`** is merged per UID.

### `reasoning_only` (`schema_version` 2)

- **`export_profile`**: `"reasoning_only"`.
- **`export_context`**: same non-secret provenance hashes as `full`.
- No **`proof_script`**, **`rubric`**, **`proof_metrics`**, or **`pareto_weight`**.

## References

- Implementation: [`lemma/validator/training_export.py`](../lemma/validator/training_export.py), epoch hook in [`lemma/validator/epoch.py`](../lemma/validator/epoch.py).
- Offline proof-metrics analyzer: [`tools/proof_metrics_analyze.py`](../tools/proof_metrics_analyze.py).
- Offline sybil/Pareto replay analyzer: [`tools/sybil_replay_analyze.py`](../tools/sybil_replay_analyze.py).
- Backlog context: [incentive-roadmap.md](incentive-roadmap.md) (training export item).
