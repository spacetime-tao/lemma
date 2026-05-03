# Generated problems (default)

When `LEMMA_PROBLEM_SOURCE=generated`, each round maps `chain_head → problem_seed` via `LEMMA_PROBLEM_SEED_MODE`: default **`quantize`** holds one theorem for each `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` window (default **100** blocks). **`subnet_epoch`** uses subnet Tempo from chain RPC instead. The seed picks one theorem from [`generated.py`](../lemma/problems/generated.py). Same code + seed ⇒ same `Problem`.

## How many problems?

There is **no single fixed “number of theorems in the world”** here. What exists today is:

- **22 template builders** (7 easy, 11 medium, 4 hard) in `_RAW_BUILDERS`: each is a function that emits a `Problem` for a given RNG seeded from the block.
- **One sampled challenge per `(seed, registry version)`**: `random.Random(seed)` picks among those builders, and many builders inject **fresh random numerals** (e.g. concrete `Nat` sums), so **infinitely many distinct statements** can appear over time even though the *family* of shapes is finite.
- **30 topic labels** (`TOPICS`) for logging / exports—algebra, analysis, combinatorics, logic, etc.—not separate proof rules.

So: **finite template repertoire, infinite instance stream** as the chain advances. If you need a **closed catalog** (countable, frozen list), use `LEMMA_PROBLEM_SOURCE=frozen` and see [catalog-sources.md](catalog-sources.md).

**Future directions** (not all implemented): more builders or splits; imports from formalized contest corpora (e.g. miniF2F-style); harder multi-lemma templates; curated `sorry` bounties alongside generated traffic—governance decides what is live.

## Template mix

- 22 builders: 7 easy, 11 medium, 4 hard (`_RAW_BUILDERS`).
- Uniform random per seed → roughly 32% / 50% / 18% easy / medium / hard.
- `TOPICS`: labels for logging; shape comes from the template.

Easy templates suit quick tactics; medium resemble typical Mathlib exercises; hard targets longer proofs.

## Timeouts

The generator does not embed limits. **Subnet policy** sets block-time / forward-wait clamps for miner answers and `LEAN_VERIFY_TIMEOUT_S` for sandbox `lake build` — one published template for all validators ([governance.md](governance.md)). Hard templates stress **prover time** first; Lean checking is usually fast for a clean script unless elaboration or cold caches blow up ([faq.md](faq.md)).

## Scoring round

Each epoch is independent: pass Lean → judge → Pareto weights for that round. Emissions follow Bittensor rules. Details: [faq.md](faq.md).

### Example

| UID | Outcome |
| --- | ------- |
| Timeout | No weight |
| Lean fails | No weight |
| Lean OK + judged | Enters Pareto pool |

Registry changes: [governance.md](governance.md). Frozen mode: [catalog-sources.md](catalog-sources.md).
