# Lemma FAQ

Plain-language answers about Lemma, Lean proofs, Bittensor roles, rewards, and
operational risks. For the full mechanism, read the [litepaper](litepaper.md).
To run the software, start with [getting-started.md](getting-started.md).

---

## What is Lemma?

**Lemma is a Bittensor subnet that rewards correct mathematical proofs.**

Every round, Lemma posts a theorem written in Lean. Miners run automated proving
systems. Validators run Lean. The proof passes or it fails.

Bitcoin rewards miners for securing the network. Bittensor rewards miners for
producing useful intelligence. Lemma rewards miners for producing correct
proofs. The analogy is not perfect, but it helps: open participants compete
under public rules, and the network rewards work that can be checked.

## Why do miners solve math?

Because proof search is hard, open-ended work. Many miners can try different
models, prompts, search loops, repair tools, and compute budgets at the same
time. Validators do the cheaper part: they check whether a submitted proof is
actually valid.

That split is the core idea. Finding proofs can be difficult. Checking proofs
with Lean is objective and reproducible.

## Are miners manually watching for theorems?

No. The current reference miner is automated software. It receives theorem
challenges from validators, calls an AI proving model or proof-search loop, and
returns a proof file when it finds one.

Human-in-the-loop flows may make sense later for longer unsolved-problem work,
but the base round design is automated.

## Who needs this math to be solved?

Mathematics sits under science, cryptography, algorithms, software, physics,
engineering, and AI reasoning. Verified proofs can become useful knowledge,
training data, benchmarks, formal libraries, and building blocks for harder
results.

Some proofs may be small. Some may only matter because they help prove something
bigger later. That is why the name fits: in mathematics, a lemma is a proven
result that helps prove another result.

## Is this subnet focused on revenue?

No. Lemma is not built around a revenue model.

The value is solved mathematics, better reasoning systems, and a growing public
record of machine-checkable proofs. How valuable that is should be decided by
the market, similar to how markets decide the value of Bitcoin's security or
Bittensor's intelligence.

## Why not start with Millennium Problems?

Because a subnet needs an economy before it can aim at the hardest problems in
the world.

If every task is nearly impossible, miners cannot learn, earn, or improve. Lemma
starts with a range of solvable theorem tasks so miners can build proof
capacity. Harder curated problem sets and winner-take-all proof rewards can come
later.

## Foundations

### What is formal mathematics?

Formal mathematics is mathematics written in a fully specified logical language.
The definitions, axioms, and allowed inference steps are fixed in advance.
Because the rules are explicit, software can check a proof line by line.

### What is a theorem?

A theorem is a precise mathematical claim: under these assumptions, this
conclusion follows. Lemma broadcasts theorem statements in Lean so every miner
works on the same target.

### What is a proof?

A proof is a correct argument for a theorem. In Lemma, the proof must be written
as code that Lean can verify. Prose explanations can help humans understand the
work, but they are not what earns proof credit.

### What is a proof script?

A `proof_script` is the source file a miner submits. It contains the proof
written in the formal language Lemma expects.

### What does a proof assistant do?

A proof assistant checks whether a proof script follows the rules of the formal
system. Lemma uses Lean. If every step is valid, Lean accepts the proof. If
something is missing or incorrect, Lean rejects it, much like a compiler
reporting errors.

### Is this "Bitcoin for math"?

Only as an analogy. Bitcoin miners compete to produce valid blocks. Lemma miners
compete to produce Lean-valid proofs for published theorem statements. Both
involve networks and tokens; the work and reward mechanics are different.

## Lean

### Why Lean?

Lean gives Lemma an objective checker. Validators do not grade style or
persuasive writing. They run the same pinned verifier against the same theorem
statement and submitted proof file.

## Bittensor roles

### What does a miner do?

A miner runs automated prover software. Validators send it theorem challenges;
the miner calls an AI proving model, a proof-search loop, or a repair loop, and
returns a Lean `proof_script` when it finds one. More detail: [miner.md](miner.md).

### What does a validator do?

A validator sends theorem challenges to miners, collects replies, verifies
submissions with Lean inside Docker, and publishes weights for eligible work.
More detail: [validator.md](validator.md).

### What does Bittensor provide?

Bittensor provides wallet accounts, a shared view of who is registered, validator
weights, and token reward flow. You still run Lemma locally with commands such
as `lemma miner ...` and `lemma validator ...`.

## Rewards at a high level

### Do miners earn alpha?

Yes. Alpha is the subnet reward token. Miners can earn alpha when their
submissions receive score under Lemma's rules. The first gate is Lean
verification: if a proof does not pass Lean, it is not eligible for proof score.
See [Rewards and Weights](litepaper.md#rewards-and-weights).

### What is the difference between testnet and mainnet?

Lemma currently runs on Bittensor testnet at the netuid listed in
[Current Status](litepaper.md#current-status). Mainnet, also called Finney, is
separate. Only rely on mainnet rewards if the Lemma deployment you are following
is registered, live, and configured for the correct network and netuid.

### What costs should I expect?

Miners may pay for prover APIs, servers, and registration fees. Validators may
pay for hardware, Docker storage, disk, and uptime. Estimate costs before
scaling.

## Risks and operations

### What key and VPS mistakes hurt the most?

Leaked keys or sloppy hosting can drain accounts or hurt reputation scores. See
[vps-safety.md](vps-safety.md).

### What operational failures are common?

Closed firewall ports, full disks, cold caches, mismatched pinned toolchains,
and drifting Docker images are common operational problems. See
[production.md](production.md).

## Software maturity

Lemma is still largely proof-of-concept software. Expect rough edges, try
testnet first, pin versions, and back up keys and config.

## Trust and fairness

### Who decides if my proof is accepted?

Lean decides whether the submitted `proof_script` proves the exact theorem
statement under the pinned toolchain. Validators do not grade style or prose
before this Lean verification gate.

### What happens after Lean accepts?

A passing proof enters Lemma's scoring rules. Those rules can evolve through
governance, but they sit after the Lean verification gate; they do not replace
it.

### Can validators cheat by changing the theorem?

Not silently on the wire. Each challenge includes the theorem id, theorem
statement, imports, and toolchain pins. Those fields participate in the synapse
body hash; transport integrity checks reject mismatched hashes, so casual
tampering between validator and miner should fail loudly instead of swapping the
theorem unnoticed.

Matching the subnet's agreed theorem is still a coordination problem, not a
chain-enforced proof. Operators should compare published pins, follow
[governance.md](governance.md), and treat drift as misconfiguration or foul play
until proven otherwise.

## Why now?

Formal theorem proving is becoming a serious AI frontier. Useful references:

- [Olympiad-level formal mathematical reasoning with reinforcement learning](https://www.nature.com/articles/s41586-025-09833-y)
- [The Millennium Prize Problems](https://www.claymath.org/millennium-problems/)
- [Formal Theorem Proving by Rewarding LLMs to Decompose Proofs Hierarchically](https://arxiv.org/abs/2411.01829)
- [List of unsolved problems in mathematics](https://en.wikipedia.org/wiki/List_of_unsolved_problems_in_mathematics)
- [Lemma in mathematics](https://en.wikipedia.org/wiki/Lemma_(mathematics))

## Practical

### Where do I start?

1. [litepaper.md](litepaper.md)
2. [getting-started.md](getting-started.md)
