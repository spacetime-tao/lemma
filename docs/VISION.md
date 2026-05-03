# Vision & roadmap

Lemma is a **Bittensor subnet** where participants answer formal math challenges in **Lean 4**: they submit a **proof script** (and, on the default path, a **reasoning trace**). Validators **verify proofs** in an isolated Lean environment (typically Docker). An **LLM judge** scores how well the trace explains the work when a trace is part of the submission. **Weights on chain** follow from that pipeline.

**Important distinction:** what the subnet *must* check mechanically is the **proof script against the locked `theorem`**. *How* that script was produced—autonomous model, human mathematician, or a mixed team—is largely **out of band** for Lean. Today’s reference miner is LLM-driven; the **bounty / long-horizon lane** is explicitly compatible with **offline work** and **human-led** formalization, as long as the final submission passes verification.

This document is for **contributors and partners** who want the long-term direction—not only the current implementation.

---

## Why Lean as the gate

Lean gives an **objective, binary check** at the kernel: either the proof type-checks against the stated `theorem`, or it does not. There is no partial credit inside the proof assistant itself. That property is what makes a decentralized grading story credible: the “grader” is not a human curve, it is **mechanical verification**.

The trade-off is discipline elsewhere: the **statement must be fixed**, the **proof must be the only editable surface**, and tooling must reject **unsound shortcuts** (for example `sorry`, rogue `axiom`s, or silently changing the goal). Lemma’s validator path encodes those constraints; tightening them over time is core work, not polish.

---

## Where we are: proof of concept → runnable subnet

The codebase already demonstrates an **end-to-end loop**: sample or generate a `Problem`, send a `LemmaChallenge`, run a prover (the bundled path is **LLM-backed**), verify with `lake` / sandbox tooling, optionally judge the trace, and participate in normal miner/validator flows. Operator tooling (`lemma` CLI, env setup, docs, CI) exists so others can reproduce that loop locally.

**Near-term bar:** a new miner can join with documented steps, run against **known-formalized** problems, and get **consistent scoring** without bespoke support.

---

## Bounty lane: offline work, any prover, submit when ready

For **hard or “unsolved” style** items (curated `sorry`, formalized Olympiad-tier statements, rare frontier prompts), the economically meaningful work often happens **off the subnet clock**:

- A person or team develops a proof using **their own editors, libraries, and CI**—the same way Mathlib contributors work today.
- They **run Lean locally** (or in their own infra) until `lake build` succeeds and they are confident the proof matches the **published statement hash** they will be judged against.
- When satisfied, they **submit** the `proof_script` (and whatever the protocol asks for alongside it, e.g. a trace) through the normal miner / challenge flow. **If verification passes, they earn the reward**; if not, they do not.

Nothing in that story *requires* an LLM to be the author of the proof. Lemma’s role is to be the **trustless checkpoint**: fixed goal, reproducible verify, transparent payout rules. **Publicizing a major result** (paper, blog, Mathlib PR) is separate from verification but encouraged culturally—and large wins can still be shared *after* the on-chain check, the same way any open-source contribution is.

The **steady, high-frequency lane** may stay automation-heavy for throughput; the **bounty lane** is where human-scale timelines (days to months) and **submit-when-ready** behavior naturally fit.

---

## Roadmap (streamlined)

Phases below are **sequenced**, not mutually exclusive—some security and problem-supply work can start early.

### 1. Economics v0 (simple, legible)

Before sophisticated game theory, the subnet needs **rules people can reason about**:

- **Two lanes:** a **high-frequency** track (steady work, predictable verify cost; often automation-friendly) and an **optional bounty** track (longer-horizon items; **offline proving** then **submit when ready**, as above).
- **Simple rewards first:** e.g. **static** emission per solved item or per epoch, plus **rollover** when no one solves a bounty—avoid early dependence on time-escalating bounties that encourage last-minute sniping.
- **Cadence tuned by lane:** e.g. ~**30 days** per bounty rotation for *curated* formalized-hard / `sorry`-class work is a reasonable default; **open conjectures** should be treated as “usually unsolved this cycle,” not “must finish in N days.”

**Goal:** miners and validators can explain payouts in one page.

### 2. Security & trust model (system around Lean)

Lean is strict; the **surrounding software** must not be the weak link:

- **Statement lock:** miners cannot substitute an easier `theorem`.
- **Proof hygiene:** reject `sorry`, control `axiom` usage, keep cheat scans and sandbox boundaries aligned with what the subnet claims to reward.
- **Operational trust:** Docker images, optional **remote verify** workers, API keys, and upgrade paths (pins, meta hashes) documented and testable.

**Goal:** a short **threat model** plus a validator checklist that matches production behavior.

### 3. Problem supply & difficulty pipeline

A live subnet needs a **curated feed** of problems—not only generators, but **governance** over difficulty, verify time, and rotation:

- **Tiers** (e.g. easy → extreme) backed by **catalog or generated** sources, with explicit **verify budgets**.
- **“Unsolved” / bounty lane:** mostly **Mathlib-style `sorry`** cleanup and similar formalized gaps (high value, bounded difficulty variance); **rare** true frontier items only with clear expectations. Solvers may work **offline** and **submit when ready** (see **Bounty lane** above).
- **Automation + human gates** so an epoch does not randomly alternate between trivial and intractable.

**Goal:** every live challenge has a **known class**, **expected verify cost**, and **clear rotation policy**.

### 4. Scale & operations

Under load: queueing, timeouts, cost of verification vs judge calls, observability, and **runbooks** for stuck verifies, RPC drift, or bad releases.

**Goal:** the subnet survives **N miners** without manual firefighting for known failure modes.

### 5. Advanced incentives (evidence-driven)

After real traffic: consider **partial-progress** or **lemma-submission** tracks, anti-collusion tweaks, and richer scoring—**only** where the protocol can define rewards without breaking the Lean gate’s clarity.

**Goal:** incentive changes follow **measured** miner behavior, not pre-launch theory alone.

---

## Through-line

**Lean verification stays the objective floor.** Everything else—judges, traces, economics—exists to make that floor **useful, fair, and sustainable** on a decentralized network.

---

## Related docs

| Doc | Use |
| --- | --- |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Components and data flow today. |
| [GOVERNANCE.md](GOVERNANCE.md) | Pins, meta, policy. |
| [GETTING_STARTED.md](GETTING_STARTED.md) | Install and first commands. |
| [MINER.md](MINER.md) / [VALIDATOR.md](VALIDATOR.md) | Operator detail. |
