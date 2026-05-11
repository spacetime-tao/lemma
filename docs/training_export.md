# Training Export

Validators can write one JSON object per scored miner response each epoch.

Enable it with:

```bash
LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/train.jsonl
```

Lemma does not upload exports. Operators rotate, store, or ship files
themselves. See
[`scripts/training_export_upload_example.sh`](../scripts/training_export_upload_example.sh).

## Profiles

Set:

```bash
LEMMA_TRAINING_EXPORT_PROFILE=summary
```

| Profile | Schema | Contains | Use |
| --- | --- | --- | --- |
| `full` | 1 | Theorem, proof, public coldkey when available, optional labels, optional proof metrics, `export_context`, and `pareto_weight`. | Private research and replay. |
| `summary` | 2 | Block, theorem id, UID, model card, and non-secret `export_context`. | Lightweight operations. |

`summary` does not include proof text, labels, proof metrics, or Pareto weight.

## Proof-Metrics Calibration

Use this only for private research.

```bash
LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/proof-metrics.jsonl
LEMMA_TRAINING_EXPORT_PROFILE=full
LEMMA_LEAN_PROOF_METRICS=1
```

`LEMMA_LEAN_PROOF_METRICS=1` adds one compare-only Lean probe after a proof
already passes. It does not change rewards or weights.

Checklist:

1. Pick a private export path.
2. Do not commit or publish the export.
3. Collect varied successful proofs, including multiple UIDs on the same theorem
   ids.
4. Save the `.env` and validator settings used for the run.
5. Run the analyzer:

   ```bash
   uv run python -m tools.proof_metrics_analyze /var/lib/lemma/proof-metrics.jsonl
   ```

6. Keep the analyzer output beside the export.
7. Treat `gate_verdict=research_only` as a hard stop for scoring changes.

Look first at:

- `decision_data_blockers`;
- `decision_data_gaps`;
- `export_context`;
- successful versus failed probe rows;
- within-theorem comparisons;
- padding outliers;
- same-theorem disagreement examples.

For release checklists:

```bash
uv run python -m tools.proof_metrics_analyze /var/lib/lemma/train.jsonl --require-decision-ready
```

This only checks readiness for human review. It does not approve a scoring
change.

The fixture at `tests/fixtures/proof_metrics_validation.jsonl` tests the
analyzer. It is not scoring evidence.

Decision guidance: [proof-intrinsic-decision.md](proof-intrinsic-decision.md).

## Sybil/Pareto Replay

Use a private `full` export to evaluate Sybil/Pareto reward changes.

```bash
uv run python -m tools.sybil_replay_analyze /var/lib/lemma/train.jsonl
```

The helper compares:

- current same-coldkey partition;
- no partition;
- legacy identical-proof grouping;
- exact-copy pressure;
- lightly rewritten K-miner pressure.

If old exports lack coldkeys, coldkey replay assumes one coldkey per UID. That
is still useful for clone pressure, but not proof that partitioning is sybil
resistance.

For release checklists:

```bash
uv run python -m tools.sybil_replay_analyze /var/lib/lemma/train.jsonl --require-decision-ready
```

Copy summary lines into [sybil_economics.md](sybil_economics.md). Do not publish
the private JSONL.

## Gaming And Leakage

Exports can leak useful training or gaming signals:

- labels can teach models to chase labels;
- proof scripts are full solutions;
- `pareto_weight` exposes reward outcomes;
- `proof_metrics` exposes research signals.

Use `summary` when you only need operations provenance.

For public release, aggregate or post-process further. `theorem_id`, `uid`, and
`block` can still reveal structure when combined with other data.

The old `reasoning_only` value is accepted as a legacy alias for `summary`.

## Schema Reference

### `full`

- `export_profile`: `"full"`.
- `schema_version`: `1`.
- `export_context`: non-secret hashes for the run.
- `theorem_statement`, `proof_script`, and optional labels.
- `coldkey` when the metagraph provides it.
- `proof_metrics` when `LEMMA_LEAN_PROOF_METRICS=1`.
- `pareto_weight` after weights are computed.

### `summary`

- `export_profile`: `"summary"`.
- `schema_version`: `2`.
- `export_context`: same non-secret hashes as `full`.
- No `proof_script`, labels, `proof_metrics`, or `pareto_weight`.

## References

- [`lemma/validator/training_export.py`](../lemma/validator/training_export.py)
- [`lemma/validator/epoch.py`](../lemma/validator/epoch.py)
- [`tools/proof_metrics_analyze.py`](../tools/proof_metrics_analyze.py)
- [`tools/sybil_replay_analyze.py`](../tools/sybil_replay_analyze.py)
- [workplan.md](workplan.md)
