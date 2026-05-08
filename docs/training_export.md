# Training export (validator JSONL)

Validators optionally append one JSON object per **successfully judged** miner response each epoch when **`LEMMA_TRAINING_EXPORT_JSONL`** is set. Lemma **does not upload** files; operators rotate or ship logs themselves ([`scripts/training_export_upload_example.sh`](../scripts/training_export_upload_example.sh), [production.md](production.md)).

## Profiles (`LEMMA_TRAINING_EXPORT_PROFILE`)

| Profile | Schema | Contents | Use when |
| --- | --- | --- | --- |
| **`full`** (default) | `schema_version` **1** | `reasoning_*`, `proof_script`, `rubric` (coherence / exploration / clarity / composite), plus **`pareto_weight`** after weights are computed | Internal research, calibration, full offline replay |
| **`reasoning_only`** | `schema_version` **2** | Same reasoning fields + `block`, `theorem_id`, `uid`, `model_card`; **no** proof text, **no** rubric, **no** `pareto_weight` | Sharing datasets more broadly, PRM-style trace data with weaker direct judge/incentive labels |

Set in `.env`:

```bash
LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/train.jsonl
LEMMA_TRAINING_EXPORT_PROFILE=reasoning_only
```

## Gaming and leakage (why `reasoning_only` exists)

Exports are **not** a neutral “public good.” Depending on fields, they can teach models to:

- **Optimize the rubric** — `rubric` exposes the exact scalar judge targets validators optimize.
- **Copy proofs** — `proof_script` is a full solution for `theorem_id` at `block`.
- **Optimize incentives** — `pareto_weight` ties rows to the subnet weight map.

**`reasoning_only`** removes proof text, judge scores, and Pareto weights. It **does not** remove all structure: `theorem_id`, `uid`, and `block` still support stratification or deanonymization risks if combined with other data. For maximum privacy, post-process or aggregate before publication.

## Schema reference

### `full` (`schema_version` 1)

- **`proof_script`**, **`rubric`**: see [`training_export.py`](../lemma/validator/training_export.py).
- After the epoch, **`pareto_weight`** is merged per UID.

### `reasoning_only` (`schema_version` 2)

- **`export_profile`**: `"reasoning_only"`.
- No **`proof_script`**, **`rubric`**, or **`pareto_weight`**.

## References

- Implementation: [`lemma/validator/training_export.py`](../lemma/validator/training_export.py), epoch hook in [`lemma/validator/epoch.py`](../lemma/validator/epoch.py).
- Backlog context: [incentive-roadmap.md](incentive-roadmap.md) (training export item).
