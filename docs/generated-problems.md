# Generated problems

Generated templates are one lane inside the default `LEMMA_PROBLEM_SOURCE=hybrid` supply. Setting `LEMMA_PROBLEM_SOURCE=generated` keeps only this lane for rollback or focused testing.

Each round maps `chain_head → problem_seed` via `LEMMA_PROBLEM_SEED_MODE`: default **`quantize`** holds one theorem for each `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` window (default **100** blocks). **`subnet_epoch`** uses subnet Tempo from chain RPC instead. The seed picks one theorem from [`generated.py`](../lemma/problems/generated.py). Same code + seed ⇒ same generated `Problem`.

## How many problems?

There is **no single fixed “number of theorems in the world”** here. What exists today is:

- **100 template builders** (12 easy, 41 medium, 42 hard, 5 extreme) in `_RAW_BUILDERS`: each is a function that emits a `Problem` for a given RNG seeded from the block.
- **One sampled challenge per `(seed, registry version)`**: `random.Random(seed)` first uses the published **10% / 35% / 50% / 5% easy / medium / hard / extreme** split weights, then picks within that split. Every generated builder injects seed-chosen structure and has more than one normalized theorem shape, so **infinitely many distinct statements** can appear over time even though the *family* of shapes is finite.
- **Template-owned topic labels** (`TOPICS`) for logging / exports—algebra, analysis, combinatorics, logic, etc.—not separate proof rules and not randomly assigned.

So: **finite template repertoire, infinite instance stream** as the chain advances. The default hybrid source mixes this with a curated catalog lane; see [catalog-sources.md](catalog-sources.md).

### Plain English

What **100 builders** means is **not** “there are only 100 problems total.” It means **100 recipes**. Each recipe says how to cook one *kind* of challenge—e.g. ask for a proof about natural-number arithmetic, induction, modular arithmetic, list structure, set algebra, finite sets, real inequalities, matrices, prime existence, continuity, finite averages, graph adjacency, Diophantine witnesses, difference quotients, group laws, or rare multi-step stretch problems. Every time the subnet advances and hands out a **new seed**, the code runs the RNG again: it may pick **another recipe**, or the **same recipe with a different theorem shape, constants, finite domain, shift, or witness**.

You should **not** picture a short list to memorize. You picture **many instances** flowing from **a cookbook** with explicit split weights. The **topic** labels (algebra, analysis, …) are mainly for logging—they are not separate rule sets in Lean.

**Honest limit:** these are **variations inside fixed templates**, not “every possible theorem in mathematics.” Over time, miners may still recognize the builder families—that is normal. **More diversity** comes from higher-quality builders, the curated catalog lane, and later campaign/bounty lanes. See [problem-supply-policy.md](problem-supply-policy.md) for the explicit predictability boundary.

**Future directions** (not all implemented): more builders or splits; imports from formalized contest corpora (e.g. miniF2F-style); harder multi-lemma templates; curated `sorry` bounties alongside generated traffic—governance decides what is live.

## Adding new families

Add new generated families only when they increase real theorem-shape diversity. Prefer a new algebraic, combinatorial, order, set, list, matrix, continuity, or number-theory pattern over another near-copy of an existing tactic exercise.

Checklist for a new family:

- append the builder to `_RAW_BUILDERS`; do not reorder existing builders;
- make the theorem depend on the seed through meaningful constants, finite domains, shifts, witnesses, or small concrete structures;
- keep at least two normalized theorem shapes across the generated-source variation seed set;
- provide an instance-specific `informal_statement` that remains readable above the formal theorem;
- include a complete public witness proof and keep the advertised split honest;
- run the generated-template gate, including the Docker Lean build before release;
- record the new generated and hybrid registry hashes in release notes.

Do not add a builder whose only variation is a hidden dummy marker or whose public text would need to say “displayed generated theorem.” If a family cannot vary naturally, leave it out until there is a better formulation.

## Template mix

- 100 builders: 12 easy, 41 medium, 42 hard, 5 extreme (`_RAW_BUILDERS`).
- Explicit default split weights: 10% easy, 35% medium, 50% hard, 5% extreme.
- `TOPICS`: template-owned labels for logging; shape comes from the template.

Easy templates suit quick tactics; medium resemble typical Mathlib exercises; hard targets longer proofs; extreme is a rare stretch tier for multi-step proofs inside the steady cadence. Off-cadence campaign or bounty work remains a separate lane with different deadlines and reward policy.

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
