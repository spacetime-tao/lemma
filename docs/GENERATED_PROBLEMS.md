# Generated problems (default)

When `LEMMA_PROBLEM_SOURCE=generated`, each round maps `chain_head → problem_seed` via `LEMMA_PROBLEM_SEED_MODE`: default `subnet_epoch` uses subnet Tempo; `quantize` uses `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`. The seed picks one theorem from [`generated.py`](../lemma/problems/generated.py). Same code + seed ⇒ same `Problem`.

## Template mix

- 22 builders: 7 easy, 11 medium, 4 hard (`_RAW_BUILDERS`).
- Uniform random per seed → roughly 32% / 50% / 18% easy / medium / hard.
- `TOPICS`: labels for logging; shape comes from the template.

Easy templates suit quick tactics; medium resemble typical Mathlib exercises; hard targets longer proofs.

## Timeouts

The generator does not embed limits. **Subnet policy** sets `DENDRITE_TIMEOUT_S` (miner answer) and `LEAN_VERIFY_TIMEOUT_S` (sandbox `lake build`) — one published template for all validators ([GOVERNANCE.md](GOVERNANCE.md)). Hard templates stress **prover time** first; Lean checking is usually fast for a clean script unless elaboration or cold caches blow up ([FAQ.md](FAQ.md)).

## Scoring round

Each epoch is independent: pass Lean → judge → Pareto weights for that round. Emissions follow Bittensor rules. Details: [FAQ.md](FAQ.md).

### Example

| UID | Outcome |
| --- | ------- |
| Timeout | No weight |
| Lean fails | No weight |
| Lean OK + judged | Enters Pareto pool |

Registry changes: [GOVERNANCE.md](GOVERNANCE.md). Frozen mode: [CATALOG_SOURCES.md](CATALOG_SOURCES.md).
