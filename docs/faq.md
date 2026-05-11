# Lemma FAQ

Plain-language answers. For depth see [litepaper.md](litepaper.md); for setup see [getting-started.md](getting-started.md).

---

## What is Lemma?

**Lemma** is a [Bittensor](https://docs.learnbittensor.org/) subnet. Miners try to solve published math problems with answers a computer can check (see *Foundations* below). Validators use the same checker, so pass or fail is mechanical—not opinion.

Tokens and payouts follow normal Bittensor rules: validators publish scores for miners (weights), and miners earn the subnet reward token (alpha) under Lemma’s published scoring. Formulas and policy live in the [litepaper](litepaper.md) and [technical-reference.md](technical-reference.md).

**Rough analogy to Bitcoin:** open competition and fixed rules, but the job is finding a correct proof for a published statement, not racing to publish the next chain block. Only one miner wins each Bitcoin block; on Lemma, many miners can pass the same round if their proofs check out.

---

## Foundations

### What is formal mathematics?

It is mathematics built in a fully specified logical language: definitions, axioms, and which inference steps are allowed are fixed up front. If you write a proof in that language, software can check it line by line—each step either matches the rules or it does not.

### What is a theorem?

A **theorem** is a precise claim: “given these assumptions, this conclusion holds.” Lemma broadcasts that claim in a formal language so everyone proves the same statement.

### What is a proof?

A **proof** is a correct argument for the theorem. Here it has to be written so a checker can follow it—no gaps justified only in prose.

### What is a proof script?

The **`proof_script`** is the **actual file** (source code) the miner submits—the proof written in the formal language the subnet expects.

### What does a proof assistant do?

A **proof assistant** (**Lean**, for Lemma) reads the proof script and says whether the logic closes: yes if every step checks out, no otherwise—like a compiler that returns errors until the proof is complete.

### Is this “Bitcoin for math”?

Only as an analogy. Bitcoin miners compete for each new block; Lemma miners compete to produce proofs that pass the checker. Both involve networks and tokens; the work and the economics are different.

---

## Lean

### Why Lean?

**Lean** is the proof assistant the subnet standardizes on so every validator runs the same checker against the same pinned toolchain—no human grading prose.

---

## Bittensor roles

### What does a miner do?

A miner exposes a small network service on a port you choose so validators can send challenges (theorem plus pinned Lean toolchain details). Bittensor calls that service an **Axon**. The miner searches for a **`proof_script`** that satisfies the broadcast. More detail: [miner.md](miner.md).

### What does a validator do?

Sends challenges to miners, collects replies, runs Lean (often inside Docker so environments match), turns results into scores, and writes those scores on chain. More detail: [validator.md](validator.md).

### What does Bittensor provide?

Wallet accounts (**coldkey** / **hotkey**), a shared view of who is registered, and on-chain recording of scores and token flows. You still run Lemma locally (`lemma miner …`, `lemma validator …`).

---

## Rewards (high level)

### Do miners earn alpha?

Yes. **Alpha** is the subnet’s reward token; miners receive it when their work earns score under Lemma’s rules, starting from proofs that pass Lean. How scores map to payouts: [litepaper — Proofs, Scores, And Weights](litepaper.md#proofs-scores-and-weights).

### Testnet vs mainnet?

Lemma runs on Bittensor testnet at a published netuid (see [litepaper — Current Status](litepaper.md#current-status)). Mainnet (Finney) is different—only trust rewards there if the Lemma deployment you follow is registered and live.

### What costs should I expect?

Miners often pay for API calls (e.g. LLM provers), servers, and registration fees. Validators pay for hardware, Docker, disk, and uptime. Estimate before you scale.

---

## Risks and operations

### What key and VPS mistakes hurt the most?

Leaked keys or sloppy hosting can drain accounts or hurt reputation scores. See [vps-safety.md](vps-safety.md).

### What operational failures are common?

Closed firewall ports (validators cannot reach your miner’s listen port), full disks, cold caches, wrong pinned toolchain settings, or drifting Docker images. See [production.md](production.md).

---

## Software maturity

Lemma is still largely proof-of-concept software. Expect rough edges—try testnet first, pin versions, and back up keys and config.

---

## Trust and fairness

### Who decides if my proof is accepted?

**Lean** returns pass or fail on whether your **proof script** proves the exact broadcast statement under the pinned toolchain. There is no style ranking before that.

### What happens after Lean accepts?

Passing work feeds into Lemma’s scoring rules (see the litepaper). Those rules sit after the Lean gate; they can change with governance but do not replace verification.

### Can validators cheat by changing the theorem?

Everyone is supposed to follow the same published toolchain and artifacts ([governance.md](governance.md)). Compare hashes with the subnet when in doubt.

---

## Practical

### Where do I start?

1. [litepaper.md](litepaper.md)
2. [getting-started.md](getting-started.md)
