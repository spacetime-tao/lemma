# Vision & roadmap

Lemma is an **incentivized theorem-proving subnet** for mathematics on **Bittensor**. Participants answer formal math challenges in **Lean 4** by submitting a **proof script**. Validators **verify proofs** in **Docker** (lean-sandbox image). **Weights on chain** should center on Lean-verified proofs.

**One-sentence objective:** Lemma rewards Lean-valid proofs for published theorem statements.

Informal reasoning belongs outside the live protocol: writeups, human review,
benchmarks, or publication. The subnet reward axis is proof-only. See
[objective-decision.md](objective-decision.md) and
[proof-only-incentives.md](proof-only-incentives.md).

**Important distinction:** what the subnet *must* check mechanically is the **proof script against the locked `theorem`**. *How* that script was produced—autonomous model, human mathematician, or a mixed team—is largely **out of band** for Lean. Today’s reference miner is LLM-driven. A planned **bounty / long-horizon lane** (opt-in, higher stakes, offline-friendly) is **not** required at launch—it fits **after** the base economy is healthy (see **Economics v0 → v1** below).

This document is for **contributors and partners** who want the long-term direction—not only the current implementation. Today’s code is still largely **proof-of-concept**; you can nevertheless **run on** **Subnet 467 (Lemma)** on **Bittensor testnet** while that matures. **Finney** is mainnet—a separate network.

---

## What the subnet produces

Lemma produces **verified formal proofs**.

The digital commodity is not an informal reasoning trace, an essay, or a hidden
model chain of thought. Those artifacts may still be useful for research,
debugging, education, or human review, but they are not the live product.

The live product is a theorem/proof pair where the proof script is accepted by
Lean for the published theorem statement. Put another way: Lemma is a market for
proof search. The subnet publishes formal theorem statements; miners use AI and
compute to search for proofs; validators mechanically verify the submissions;
accepted proofs become the produced work.

That keeps the base story simple: Bitcoin miners produce valid hashes under a
difficulty rule. Lemma miners produce valid Lean proofs under a theorem rule.

For the current v0 generated lane, this is best understood as **proof capacity**:
the network is measuring whether miners and validators can reliably find,
submit, verify, and weight proofs. In later off-cadence lanes, the same mechanism
can point at curated theorem campaigns, Mathlib gaps, benchmark queues, or
human-requested theorem work.

---

## Why Lean as the gate

Lean gives an **objective, binary check** at the kernel: either the proof type-checks against the stated `theorem`, or it does not. There is no partial credit inside the proof assistant itself. That property is what makes a decentralized grading story credible: the “grader” is not a human curve, it is **mechanical verification**.

The trade-off is discipline elsewhere: the **statement must be fixed**, the **proof must be the only editable surface**, and tooling must reject **unsound shortcuts** (for example `sorry`, rogue `axiom`s, or silently changing the goal). Lemma’s validator path encodes those constraints; tightening them over time is core work, not polish.

---

## Where we are: proof of concept → runnable subnet

The codebase already demonstrates an **end-to-end loop**: sample or generate a `Problem`, send a `LemmaChallenge`, run a prover (the bundled path is **LLM-backed**), verify with `lake` / sandbox tooling, and participate in normal miner/validator flows. Operator tooling (`lemma` CLI, env setup, docs, CI) exists so others can reproduce that loop locally.

**Near-term bar:** a new miner can join with documented steps, use **known-formalized** problems locally, and get **consistent scoring** without bespoke support.

---

## Bounty lane (v1-phase): offline work, any prover, submit when ready

This lane is the **optional second track** described under **Economics v1**—rolled out once the steady lane has matured. For **hard or “unsolved” style** items (curated `sorry`, formalized Olympiad-tier statements, rare frontier prompts), the economically meaningful work often happens **off the subnet clock**:

- A person or team develops a proof using **their own editors, libraries, and CI**—the same way Mathlib contributors work today.
- They **run Lean locally** (or in their own infra) until `lake build` succeeds and they are confident the proof matches the **published statement hash** they will be judged against.
- When satisfied, they **submit** the `proof_script` through the normal miner /
  challenge flow. **If verification passes, they earn the reward**; if not, they
  do not.

Nothing in that story *requires* an LLM to be the author of the proof. Lemma’s role is to be the **trustless checkpoint**: fixed goal, reproducible verify, transparent payout rules. **Publicizing a major result** (paper, blog, Mathlib PR) is separate from verification but encouraged culturally—and large wins can still be shared *after* the on-chain check, the same way any open-source contribution is.

The **steady, high-frequency lane** stays automation-heavy for throughput at launch; the **bounty lane** is where human-scale timelines (days to months) and **submit-when-ready** behavior fit once that optional track exists.

---

## Roadmap (streamlined)

Phases below are **sequenced**, not mutually exclusive—some security and problem-supply work can start early.

### 1. Economics v0 (launch) → v1 (second lane)

**v0 — bootstrapping:** Launch with **one steady, high-frequency lane**: predictable verify cost, automation-friendly, easy for miners to participate and **earn emissions** while the subnet economy kicks off. Keep it BTC-like in spirit: publish work, verify work mechanically, pay for valid work. Prefer **simple rules** people can explain without heavy game theory—e.g. **static** emission per solved item or per epoch. **Goal:** validators and miners can describe payouts in **one page**.

**Not at launch:** the **second lane** (opt-in **bounty** / long-horizon tasks, **offline proving** then **submit when ready**, higher rewards, manual-scale work—see **Bounty lane** above). That is **v1-phase**: introduce it **after** the base economy is mature, so higher-stakes opt-in work does not compete with kicking off broad miner participation.

**v1 — when ready:** add the optional bounty track; **rollover** when no one solves a bounty; avoid early reliance on time-escalating prize clocks that encourage last-minute sniping. **Cadence** can differ by lane—e.g. ~**30 days** per bounty rotation for *curated* formalized-hard / `sorry`-class work; **open conjectures** stay “usually unsolved this cycle,” not “must finish in N days.”

### 2. Security & trust model (system around Lean)

Lean is strict; the **surrounding software** must not be the weak link:

- **Statement lock:** miners cannot substitute an easier `theorem`.
- **Proof hygiene:** reject `sorry`, control `axiom` usage, keep cheat scans and sandbox boundaries aligned with what the subnet claims to reward.
- **Operational trust:** Docker images, optional **remote verify** workers, API keys, and upgrade paths (pins, meta hashes) documented and testable.

**Goal:** a short **threat model** plus a validator checklist that matches production behavior.

### 3. Problem supply & difficulty pipeline

A live subnet needs a **curated feed** of problems—not only generators, but **governance** over difficulty, verify time, and rotation:

- **Tiers** (e.g. easy → extreme) backed by **catalog or generated** sources, with explicit **verify budgets**.
- **“Unsolved” / bounty lane (v1):** mostly **Mathlib-style `sorry`** cleanup and similar formalized gaps (high value, bounded difficulty variance); **rare** true frontier items only with clear expectations. Solvers may work **offline** and **submit when ready** (see **Bounty lane** above)—rolled out after the steady lane is stable.
- **Automation + human gates** so an epoch does not randomly alternate between trivial and intractable.

**Goal:** every live challenge has a **known class**, **expected verify cost**, and **clear rotation policy**.

### 4. Scale & operations

Under load: queueing, timeouts, verification cost, optional prose-evaluation cost, observability, and **runbooks** for stuck verifies, RPC drift, or bad releases.

**Goal:** the subnet survives **N miners** without manual firefighting for known failure modes.

### 5. Advanced incentives (evidence-driven)

After real traffic: consider **partial-progress** or **lemma-submission** tracks and anti-collusion tweaks—**only** where the protocol can define rewards without breaking the Lean gate’s clarity.

**Goal:** incentive changes follow **measured** miner behavior, not pre-launch theory alone.

---

## Through-line

**Lemma's identity is incentivized theorem proving; Lean verification stays the objective floor.** Everything else—economics, problem supply, and operations—exists to make that floor **useful, fair, and sustainable** on a decentralized network.

---

## Related docs

| Doc | Use |
| --- | --- |
| [Architecture](architecture.md) | Components and data flow today. |
| [Governance](governance.md) | Pins, meta, policy. |
| [Objective decision](objective-decision.md) | One-sentence objective and scoring boundary. |
| [Proof-only incentives](proof-only-incentives.md) | Long-term proof-only reward design. |
| [Problem supply policy](problem-supply-policy.md) | Public generated supply boundary and builder promotion checklist. |
| [Open problem campaigns](open-problem-campaigns.md) | v1+ campaign / bounty lane for faithful open-problem formalization and submit-when-ready proofs. |
| [Getting started](getting-started.md) | Install and first commands. |
| [Miner](miner.md) / [Validator](validator.md) | Operator detail. |
