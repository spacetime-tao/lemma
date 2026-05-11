# Lemma FAQ

Plain-language answers about Lemma, Lean proofs, Bittensor roles, rewards, and operational risks. For the full mechanism, read the [litepaper](litepaper.md). To run the software, start with [getting-started.md](getting-started.md).

---

## What is Lemma?

**Lemma** is a [Bittensor](https://docs.learnbittensor.org/) subnet for formal mathematical proof. Miners try to solve published theorem statements by submitting proof scripts that Lean can check. Validators run those submissions through the same pinned verifier, so acceptance is mechanical rather than subjective.

Rewards follow Bittensor’s normal flow: validators publish miner scores, also called weights, and miners earn the subnet reward token, alpha, according to Lemma’s scoring rules. The formulas and policy details are in the [litepaper](litepaper.md) and [technical reference](technical-reference.md).

A rough analogy is Bitcoin mining: open participation, fixed rules, and competition for rewards. The work is different. Bitcoin miners compete to produce the next valid block; Lemma miners search for Lean-valid proofs for a published theorem. Multiple Lemma miners can pass the same round.

---

## Foundations

### What is formal mathematics?

Formal mathematics is mathematics written in a fully specified logical language. The definitions, axioms, and allowed inference steps are fixed in advance. Because the rules are explicit, software can check a proof line by line.

### What is a theorem?

A **theorem** is a precise claim: under these assumptions, this conclusion follows. Lemma broadcasts theorem statements in a formal language so every miner works on the same target.

### What is a proof?

A **proof** is a correct argument for a theorem. In Lemma, the proof must be written as code that a checker can verify. Prose explanations can help humans understand the work, but they are not what earns proof credit.

### What is a proof script?

A **`proof_script`** is the source file a miner submits. It contains the proof written in the formal language Lemma expects.

### What does a proof assistant do?

A **proof assistant** checks whether a proof script follows the rules of the formal system. Lemma uses **Lean**. If every step is valid, Lean accepts the proof; if something is missing or incorrect, Lean rejects it, much like a compiler reporting errors.

### Is this “Bitcoin for math”?

Only as an analogy. Bitcoin miners compete to produce the next valid block; Lemma miners compete to produce Lean-valid proofs for published theorem statements. Both involve networks and tokens; the work and reward mechanics are different.

---

## Lean

### Why Lean?

**Lean** is the proof assistant the subnet standardizes on so every validator runs the same pinned Lean verifier against the same toolchain—no human grading prose.

---

## Bittensor roles

### What does a miner do?

A miner exposes a small network service on a port you choose so validators can send challenges (theorem plus pinned toolchain details). Bittensor calls that service an **Axon**. The miner searches for a **`proof_script`** that satisfies the broadcast. More detail: [miner.md](miner.md).

### What does a validator do?

Sends challenges to miners, collects replies, verifies submissions with Lean **inside Docker** (the supported validator path uses the pinned sandbox image so every validator matches). More detail: [validator.md](validator.md).

### What does Bittensor provide?

Wallet accounts (**coldkey** / **hotkey**), a shared view of who is registered, and on-chain recording of scores and token flows. You still run Lemma locally (`lemma miner …`, `lemma validator …`).

---

## Rewards at a high level

### Do miners earn alpha?

Yes. **Alpha** is the subnet reward token. Miners can earn alpha when their submissions receive score under Lemma’s rules. The first gate is Lean verification: if a proof does not pass Lean, it is not eligible for proof score. See [Proofs, Scores, And Weights](litepaper.md#proofs-scores-and-weights).

### What is the difference between testnet and mainnet?

Lemma currently runs on Bittensor testnet at the netuid listed in [Current Status](litepaper.md#current-status). Mainnet, also called Finney, is separate. Only rely on mainnet rewards if the Lemma deployment you are following is registered, live, and configured for the correct network and netuid.

### What costs should I expect?

Miners may pay for prover APIs, servers, and registration fees. Validators may pay for hardware, Docker storage, disk, and uptime. Estimate costs before scaling.

---

## Risks and operations

### What key and VPS mistakes hurt the most?

Leaked keys or sloppy hosting can drain accounts or hurt reputation scores. See [vps-safety.md](vps-safety.md).

### What operational failures are common?

Closed firewall ports (validators cannot reach your miner’s listen port), full disks, cold caches, mismatched pinned toolchain, or drifting Docker images. See [production.md](production.md).

---

## Software maturity

Lemma is still largely proof-of-concept software. Expect rough edges—try testnet first, pin versions, and back up keys and config.

---

## Trust and fairness

### Who decides if my proof is accepted?

Lean decides whether the submitted **`proof_script`** proves the exact theorem statement under the pinned toolchain. Validators do not grade style or prose before this Lean verification gate.

### What happens after Lean accepts?

A passing proof enters Lemma’s scoring rules. Those rules can evolve through governance, but they sit after the Lean verification gate; they do not replace it.

### Can validators cheat by changing the theorem?

**Not silently on the wire.** Each challenge includes **`theorem_id`**, the full **`theorem_statement`**, imports, and toolchain pins. Those fields participate in the synapse **body hash**; transport integrity checks reject mismatched hashes, so casual tampering between validator and miner should fail loudly instead of swapping the theorem unnoticed ([transport.md](transport.md), [`lemma/protocol.py`](../lemma/protocol.py)).

**Matching the subnet’s agreed theorem** is a coordination problem, not a chain-enforced proof: validators are supposed to run the same published **problem seed → theorem** mapping and **validator profile** as the operator. A rogue or misconfigured validator could still *send* a different statement than the public registry implies—you could prove *that* statement and pass Lean, but your work would not line up with honest peers using the published `validator_profile_sha256` and registry hashes. Compare operator artifacts with **`uv run lemma meta`**, follow [governance.md](governance.md), and treat drift as misconfiguration or foul play until proven otherwise (published hashes reduce drift; they do not by themselves guarantee honest validators).

**Practical stance:** verify challenges against the subnet’s published pins; do not assume every validator is aligned until you have checked.

---

## Practical

### Where do I start?

1. [litepaper.md](litepaper.md)
2. [getting-started.md](getting-started.md)
