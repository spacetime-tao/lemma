# Generated problems

Generated templates are one lane inside the default `LEMMA_PROBLEM_SOURCE=hybrid` supply. Setting `LEMMA_PROBLEM_SOURCE=generated` keeps only this lane for rollback or focused testing.

Each round maps `chain_head → problem_seed` via `LEMMA_PROBLEM_SEED_MODE`: default **`quantize`** holds one theorem for each `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` window (default **100** blocks). **`subnet_epoch`** uses subnet Tempo from chain RPC instead. The seed picks one theorem from [`generated.py`](../lemma/problems/generated.py). Same code + seed ⇒ same generated `Problem`.

## How many problems?

There is **no single fixed “number of theorems in the world”** here. What exists today is:

- **80 template builders** (10 easy, 35 medium, 35 hard) in `_RAW_BUILDERS`: each is a function that emits a `Problem` for a given RNG seeded from the block.
- **One sampled challenge per `(seed, registry version)`**: `random.Random(seed)` first uses the published **10% / 35% / 55% easy / medium / hard** split weights, then picks within that split. Many builders inject **fresh random numerals** (e.g. concrete `Nat` sums), so **infinitely many distinct statements** can appear over time even though the *family* of shapes is finite.
- **Template-owned topic labels** (`TOPICS`) for logging / exports—algebra, analysis, combinatorics, logic, etc.—not separate proof rules and not randomly assigned.

So: **finite template repertoire, infinite instance stream** as the chain advances. The default hybrid source mixes this with a curated catalog lane; see [catalog-sources.md](catalog-sources.md).

### Plain English

What **80 builders** means is **not** “there are only 80 problems total.” It means **80 recipes**. Each recipe says how to cook one *kind* of challenge—e.g. ask for a proof about natural-number arithmetic, induction, modular arithmetic, list structure, set algebra, finite sets, real inequalities, matrices, prime existence, continuity, or group laws. Every time the subnet advances and hands out a **new seed**, the code runs the RNG again: it may pick **another recipe**, or the **same recipe with new random constants**. So **one family** can produce **endlessly many slightly different statements**: same pattern, different numbers or details.

You should **not** picture a short list to memorize. You picture **many instances** flowing from **a cookbook** with explicit split weights. The **topic** labels (algebra, analysis, …) are mainly for logging—they are not separate rule sets in Lean.

**Honest limit:** these are **variations inside fixed templates**, not “every possible theorem in mathematics.” Over time, miners may still recognize **which shapes repeat**—that is normal. **More diversity** comes from higher-quality builders, the curated catalog lane, and later campaign/bounty lanes. See [problem-supply-policy.md](problem-supply-policy.md) for the explicit predictability boundary.

**Future directions** (not all implemented): more builders or splits; imports from formalized contest corpora (e.g. miniF2F-style); harder multi-lemma templates; curated `sorry` bounties alongside generated traffic—governance decides what is live.

## Template mix

- 80 builders: 10 easy, 35 medium, 35 hard (`_RAW_BUILDERS`).
- Explicit default split weights: 10% easy, 35% medium, 55% hard.
- `TOPICS`: template-owned labels for logging; shape comes from the template.

Easy templates suit quick tactics; medium resemble typical Mathlib exercises; hard targets longer proofs.

## Timeouts

The generator does not embed limits. **Subnet policy** sets block-time / forward-wait clamps for miner answers and `LEAN_VERIFY_TIMEOUT_S` for sandbox `lake build` — one published template for all validators ([governance.md](governance.md)). Hard templates stress **prover time** first; Lean checking is usually fast for a clean script unless elaboration or cold caches blow up ([technical-reference.md](technical-reference.md)).

## Scoring round

Each epoch is independent: pass Lean → proof-only scoring → weights for that round. Emissions follow Bittensor rules. Details: [technical-reference.md](technical-reference.md).

### Example

| UID | Outcome |
| --- | ------- |
| Timeout | No weight |
| Lean fails | No weight |
| Lean OK + scored | Can enter live weighting |

Registry changes: [governance.md](governance.md). Predictability and release checklist: [problem-supply-policy.md](problem-supply-policy.md). Frozen mode: [catalog-sources.md](catalog-sources.md).
