# Lemma FAQ

Plain-language answers. For the full picture see [litepaper.md](litepaper.md); for setup see [getting-started.md](getting-started.md).

---

## What is Lemma?

**Lemma** is a [Bittensor](https://docs.learnbittensor.org/) **subnet**. It **rewards miners who solve published math problems** with answers a **computer can check** (see *Foundations* below). **Validators** run the same checker as everyone else, so **pass or fail** is not a matter of taste.

When proofs pass, **how credit turns into tokens** is handled by Bittensor’s usual machinery: validators publish **weights** (scores for each miner), and miners earn **alpha**, the subnet’s **reward token**. The exact formulas live with the subnet parameters—start with the [litepaper](litepaper.md), then [technical-reference.md](technical-reference.md) if you need numbers.

**Analogy:** Same rough shape as Bitcoin—open competition, fixed rules—but the work is finding a **correct proof** of a published statement, not racing for the next chain block. One difference: for each Bitcoin **block**, only **one** miner wins that round. On Lemma, **any** miner whose proof **passes the checker** for that round counts as passing the gate (how much **alpha** each one gets still follows **weight** rules).

---

## Foundations

### What is formal mathematics?

Math written so precisely that software can tell whether each step is legal—logic plus definitions, no appeal to “you know what I mean.”

### What is a theorem?

A **theorem** is a precise claim: “given these assumptions, this conclusion holds.” Lemma **broadcasts** that claim in a formal language so everyone proves the **same** statement.

### What is a proof?

A **proof** is a correct argument for the theorem. Here it has to be written so a checker can follow it—no gaps justified only in prose.

### What is a proof script?

The **`proof_script`** is the **actual file** (source code) the miner submits—the proof written in the formal language the subnet expects.

### What does a proof assistant do?

A **proof assistant** (**Lean**, for Lemma) is a program that reads the proof script and says whether the logic closes: yes if every step checks out, no otherwise—like a compiler that returns **errors** until the proof is complete.

### Is this “Bitcoin for math”?

**Only as an analogy.** Bitcoin’s miners race on hash puzzles; Lemma’s miners race on **finding proofs**. Both use decentralized networks and tokens, but the work and the assets are different systems.

---

## Lean

### Why Lean?

**Lean** is the proof assistant the subnet standardizes on so **every validator runs the same checker** on the same pins—no human jury scoring paragraphs.

---

## Bittensor roles

### What does a miner do?

A miner runs an **Axon**—Bittensor’s word for the **network service your miner exposes** so validators can send it challenges (theorem + environment pins). You choose a **port**; validators connect to it like any server. The miner searches for a **`proof_script`** that matches the broadcast. More detail: [miner.md](miner.md).

### What does a validator do?

Sends challenges to miners, collects replies, **runs Lean** (often inside **Docker** so the environment matches), computes scores, and participates in **weight-setting** on the chain. More detail: [validator.md](validator.md).

### What does Bittensor provide?

Shared **identity** (keys), **discovery** (who is registered), and **settlement** (recording weights and distributing **alpha**). You still run **Lemma’s software** locally (`lemma miner …`, `lemma validator …`).

---

## Rewards (high level)

### Do miners earn alpha?

**Alpha** is Bittensor’s usual name for the **subnet’s reward token**. Whether you earn any, and how much, depends on **live subnet parameters**, registration, and whether you are on **testnet** or **mainnet**—same as any subnet. Lemma ties rewards to **proofs that pass Lean**; see [litepaper — Proofs, Scores, And Weights](litepaper.md#proofs-scores-and-weights).

### Testnet vs mainnet?

Lemma has run on **Bittensor testnet** with a published **netuid** (see [litepaper — Current Status](litepaper.md#current-status)). **Mainnet** (**Finney**) is separate: rewards there only exist if this subnet (or a fork you trust) is **registered there**. Always confirm **network**, **RPC endpoint**, and **netuid**.

### What costs should I expect?

Miners often pay for **API calls** (e.g. LLM provers), **servers**, and **registration** fees. Validators pay for **hardware**, **Docker**, **disk**, and **uptime**. Estimate before you scale.

---

## Risks and operations

### What key and VPS mistakes hurt the most?

Leaked keys or sloppy hosting can drain accounts or get you slashed in reputation. See [vps-safety.md](vps-safety.md).

### What operational failures are common?

Closed **firewall** ports (validators cannot reach your **Axon**), full disks, cold caches, wrong **pins**, or drifting Docker images. See [production.md](production.md).

---

## Software maturity

Lemma is still largely **proof-of-concept** software. Expect rough edges—**try testnet first**, **pin versions**, and **back up keys** and config.

---

## Trust and fairness

### Who decides if my proof is accepted?

**Lean** returns **pass/fail** on whether your **proof script** proves the **exact broadcast statement** under the pinned toolchain. There is no separate “beauty contest” before that.

### What happens after Lean accepts?

The subnet’s **scoring rules** (documented in the litepaper) turn passing work into **weights** and thus **alpha**. Those rules can change with governance; they sit **after** the Lean gate, not instead of it.

### Can validators cheat by changing the theorem?

Everyone is supposed to follow the same **published pins** and artifacts ([governance.md](governance.md)). Compare hashes with the subnet when in doubt.

---

## Practical

### Where do I start?

1. [litepaper.md](litepaper.md)  
2. [getting-started.md](getting-started.md)  

### Is Lemma “LLM chat grading”?

No. A chatbot might **help you draft** a proof offline, but the **live requirement** is a **proof script the checker accepts**—not a graded conversation.
