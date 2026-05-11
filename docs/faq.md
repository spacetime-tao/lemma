# Lemma FAQ

Short answers for newcomers. The narrative overview is in [litepaper.md](litepaper.md); operators should still follow [getting-started.md](getting-started.md).

---

## Basics

### What is Lemma?

Lemma is a [Bittensor](https://docs.learnbittensor.org/) subnet that pays for **formal math proofs**—proofs written so a computer can check them mechanically. See the [litepaper](litepaper.md).

### What is Lean?

**Lean** is a proof assistant: you write mathematics as code, and Lean checks each step. If Lean accepts your proof, you really proved the stated theorem (within the rules of the logical system), not just argued informally.

Lemma uses Lean so validators do not have to “pick the best explanation”—they run the same checker everyone agrees on.

### What does Bittensor do here?

Bittensor is the coordination layer: wallets, chain registration, incentives, and weight-setting. Lemma plugs into that so miners and validators can find each other and so rewards follow subnet rules. You still run Lemma software locally (`lemma miner …`, `lemma validator …`).

### Is Lemma the same as ChatGPT proving math?

No. Miners may use LLMs **inside** their setup to search for a proof, but the **live reward path** is not “grade the chat transcript.” The gate is: **did you return a proof script Lean accepts for the published theorem?** See [litepaper — What Lemma Is Not](litepaper.md#what-lemma-is-not).

---

## Roles

### What does a miner do?

A miner runs an Axon service. When a validator sends a challenge (theorem statement + pinned toolchain), the miner tries to produce a **`proof_script`**—Lean source that proves exactly what was asked. See [miner.md](miner.md).

### What does a validator do?

A validator broadcasts challenges, waits for responses, **runs Lean** to verify proofs inside the pinned sandbox (usually Docker), aggregates scoring policy, and participates in on-chain weights. See [validator.md](validator.md).

---

## Money, risk, and expectations

### Can I earn money?

Subnet incentives exist on chain, but economics change over time. Lemma software is still largely **proof-of-concept**—treat rewards as uncertain until you understand subnet mechanics and costs (API keys, GPUs, VPS, registration).

### What can go wrong?

- **Keys**: leaked coldkeys or poor VPS hygiene are catastrophic. See [vps-safety.md](vps-safety.md).
- **Ops**: validators need reliable Docker, disk, and caches; miners need reachable Axons and working prover APIs. See [production.md](production.md).
- **Software bugs**: like any early subnet codebase—run testnet first, read docs, pin versions.

---

## Trust and fairness

### Who decides if my proof is “good”?

**Lean decides pass/fail** on the proof script for the published statement. After that, subnet **policy** decides how passing work becomes weights (that layer can evolve—see [litepaper — Proofs, Scores, And Weights](litepaper.md#proofs-scores-and-weights)).

### Can validators cheat by changing the theorem?

Validators must align with published pins and shared artifacts ([governance.md](governance.md)). You still operate in an adversarial environment—run known-good configs and compare hashes/profiles with the subnet when in doubt.

---

## Practical

### Testnet vs mainnet?

Lemma has run on **Bittensor testnet** with a specific netuid (see [litepaper — Current Status](litepaper.md#current-status)). Mainnet (“Finney”) is a different deployment context—always verify endpoints and netuid for the network you intend.

### Where do I start?

1. [litepaper.md](litepaper.md) — why Lemma exists  
2. [getting-started.md](getting-started.md) — install, wallets, first commands  

### Where is the FAQ linked?

From the [README](../README.md) docs index and from the litepaper “Start Here” section.
