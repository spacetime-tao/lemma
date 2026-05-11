# Lemma FAQ

Short answers for newcomers. The story arc is in [litepaper.md](litepaper.md); hands-on steps are in [getting-started.md](getting-started.md).

---

## What is Lemma?

Lemma is a [Bittensor](https://docs.learnbittensor.org/) subnet that **rewards miners for solving formal mathematics**: published theorem statements, answers given as **Lean proof scripts**, checked **mechanically** by the Lean proof assistant. Validators run the same checks so everyone agrees on pass/fail before subnet policy turns passes into **weight** and **alpha**. Read the [litepaper](litepaper.md).

**Analogy:** Bitcoin miners compete to produce hashes under a difficulty rule; Lemma miners compete to produce **Lean-valid proofs** under a **theorem rule**—same broad “competitive verification” shape, different puzzle.

---

## Foundations

### What is formal mathematics?

Mathematics written with enough precision that a computer can check whether each
step follows the rules (logic + definitions). Lemma lives in that world: the
question is whether the proof **script** is valid, not whether a paragraph
“sounds right.”

### What is a theorem?

A **theorem** is a precise mathematical claim: “under these definitions and
assumptions, this conclusion holds.” In Lemma, the subnet **publishes** the
theorem you must prove—usually as formal Lean source tied to a pinned
environment.

### What is a proof?

A **proof** is a correct argument that establishes the theorem. In formal math,
that argument is written so every step can be checked—no hand-waving.

### What is a proof script?

The **`proof_script`** is the Lean **source code** the miner returns: the file
(or module body) that closes the published theorem. If Lean builds it and all
goals are solved, the proof is accepted for that check; if not, it is rejected.

### What does a proof assistant do?

A **proof assistant** (here, **Lean**) is software that checks whether your
proof script actually proves the statement you claim—like a very strict compiler
for mathematics.

### Is this “Bitcoin for math”?

**Partly, as metaphor.** Both involve permissionless competition under published
rules and on-chain incentives. Lemma’s “work” is **valid formal proof**, not
hash preimage; emissions are **subnet alpha** and policy, not Bitcoin’s Halving
schedule. Do not treat Lemma as a cryptocurrency investment guide—understand
subnet mechanics and costs first.

---

## Lean

### Why Lean?

**Lean** checks proofs mechanically. Validators do not vote on whether an answer
“feels” correct; they run Lean in a pinned environment so results line up across
nodes.

---

## Bittensor roles

### What does a miner do?

Runs an Axon service. When a validator sends a challenge (theorem + toolchain
pins), the miner searches for a **`proof_script`** that proves exactly what was
published. Details: [miner.md](miner.md).

### What does a validator do?

Broadcasts challenges, collects responses, **runs Lean** (typically in Docker),
applies scoring policy, and participates in **weights** on chain. Details:
[validator.md](validator.md).

### What does Bittensor provide?

Peer discovery, registration, incentive plumbing, and weight-setting so subnets
can allocate **alpha** according to their rules. You still run Lemma locally
(`lemma miner …`, `lemma validator …`).

---

## Incentives and alpha

### Do miners earn alpha?

Subnets emit **alpha** according to their incentive mechanism. Lemma ties that
mechanism to **Lean-valid proof work** (see [litepaper — Proofs, Scores, And Weights](litepaper.md#proofs-scores-and-weights)). **Economics change** with registration,
liquidity, and subnet parameters—nothing here is financial advice.

### Testnet vs mainnet?

Lemma has operated on **Bittensor testnet** with a published netuid (see
[litepaper — Current Status](litepaper.md#current-status)). **Mainnet (Finney)** is a
different deployment: alpha there only exists if a subnet deployment is
**registered on mainnet** with live emissions. Always verify **network, endpoint,
and netuid** for the environment you use.

### What costs should I expect?

Even when alpha is available, miners typically pay for **inference APIs**, **GPU
or VPS** hosting, and **chain registration** fees. Validators pay for **hardware,
Docker images, disk**, and operations. Budget before you scale.

---

## Risks and operations

### What key and VPS mistakes hurt the most?

Coldkey compromise or unsafe VPS practice can lose funds and reputation. See
[vps-safety.md](vps-safety.md).

### What operational failures are common?

Unreachable Axon ports, exhausted disk on validators, cold Lean caches, mis-set
pins versus the subnet, or Docker drift. See [production.md](production.md).

---

## Software maturity

Lemma’s codebase is still largely **proof-of-concept**. Expect bugs; **run on
testnet first**, read release notes, **pin versions**, and keep backups of keys
and config.

---

## Trust and fairness

### Who decides if my proof is accepted?

**Lean** gives **pass/fail** on whether your **proof script** proves the **exact
published statement** under the pinned toolchain and policy—there is no separate
human “quality score” before that.

### What happens after Lean accepts?

**Subnet policy** decides how accepted work becomes **weights** and thus **alpha
allocation** among miners ([litepaper — Proofs, Scores, And Weights](litepaper.md#proofs-scores-and-weights)). That layer can evolve with governance; it does not
replace the Lean gate.

### Can validators cheat by changing the theorem?

Validators are expected to align with published **pins** and shared artifacts
([governance.md](governance.md)). You still operate in an adversarial world—run
configs that match the subnet and verify hashes when unsure.

---

## Practical

### Where do I start?

1. [litepaper.md](litepaper.md) — what Lemma is  
2. [getting-started.md](getting-started.md) — install, keys, first commands  

### Is Lemma “LLM chat grading”?

No. A model may **help you find** a proof **offline**, but the **live gate** is
whether you submitted a **proof script Lean accepts** for the broadcast—not a
graded conversation transcript.
