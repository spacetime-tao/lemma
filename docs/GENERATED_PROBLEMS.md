# Generated problems (default)

When **`LEMMA_PROBLEM_SOURCE=generated`**, each epoch uses the chain block as an integer seed and selects **one** theorem from a fixed template list in [`lemma/problems/generated.py`](../lemma/problems/generated.py). Identical code + seed ⇒ identical `Problem`.

## Template mix

- **22** builders: **7** `easy`, **11** `medium`, **4** `hard` (`_RAW_BUILDERS`).
- Uniform random choice per seed → roughly **32% / 50% / 18%** easy / medium / hard.
- **`TOPICS`**: 30 labels for logging only; problem **shape** comes from the template.

Easy templates suit automation (`rfl`, `norm_num`, …); medium templates resemble typical Mathlib exercises; hard templates target longer proofs.

## Timeouts

The generator does not embed a time limit. **`DENDRITE_TIMEOUT_S`** limits the validator→miner HTTP wait for that challenge (default **3600** s). **`LEAN_VERIFY_TIMEOUT_S`** limits sandbox build time (default **3600** s). Validators should agree on both ([GOVERNANCE.md](GOVERNANCE.md)).

Hard templates often fail or time out under tight budgets depending on model and hardware.

## Scoring round

Each epoch is independent: pass Lean → judge trace → Pareto weights for that round only. Chain emissions follow Bittensor consensus ([Learn Bittensor — emissions / weights](https://learnbittensor.org/)). Details: [FAQ.md](FAQ.md).

### Example (illustrative)

| UID | Outcome |
| --- | ------- |
| Timeout | No weight |
| Lean fails | No weight |
| Lean OK + judged | Enters Pareto pool |

Governance for registry changes: [GOVERNANCE.md](GOVERNANCE.md). Frozen catalog mode: [CATALOG_SOURCES.md](CATALOG_SOURCES.md).
