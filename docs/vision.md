# Vision & roadmap

**Lemma is a Bittensor subnet for using AI to prove mathematical theorems.**

Lemma posts theorem challenges. Miners use AI to write Lean proof files.
Validators use Lean to check them. Valid proofs become eligible for miner
rewards.

Bitcoin rewards miners for securing the network. Bittensor rewards miners for
producing useful intelligence. Lemma rewards miners for producing correct
proofs. The value is solved mathematics, better reasoning systems, and a growing
public record of computer-verified proofs. The market decides how valuable that
is.

**One-sentence objective:** Lemma rewards Lean-valid proofs for published theorem
statements.

The subnet reward axis is proof verification. See
[objective-decision.md](objective-decision.md) and
[proof-verification-incentives.md](proof-verification-incentives.md).

This document is for contributors and partners who want the long-term direction,
not only the current implementation. Today's code is still proof-of-concept
software, but it can already run on **Subnet 467 (Lemma)** on **Bittensor
testnet**. **Finney** is mainnet, a separate network.

---

## What the subnet produces

Lemma produces **verified formal proofs**.

The live product is a theorem/proof pair where the proof script is accepted by
Lean for the published theorem statement. The subnet publishes formal theorem
statements; miners use AI proving systems; validators mechanically verify the
submissions; accepted proofs become the produced work.

That keeps the base story simple: Bitcoin miners produce valid blocks under
public rules. Lemma miners produce valid Lean proofs under a theorem rule.

---

## Current foundation

Lean gives an objective mechanical check: either the proof type-checks against
the stated theorem, or it does not. Lemma's surrounding software exists to keep
that check honest and reproducible:

- the theorem statement is fixed for the challenge;
- the proof script is the editable artifact;
- validators reject unfinished proofs and attempts to add new assumptions;
- the Lean toolchain, Mathlib revision, and validator profile are pinned;
- dashboard exports publish safe summary data, not raw proof scripts.

These are not a separate future business phase. They are the foundation of the
subnet. Future work should keep hardening them as traffic grows.

---

## Problem supply and difficulty

Lemma should continually broaden its theorem supply while keeping every live
challenge reproducible.

The generated lane can cover natural-number arithmetic, induction, finite sums,
divisibility, modular arithmetic, primes, real polynomial identities, real
inequalities, continuity, absolute values, finite sets, set algebra, logic,
function composition, matrices, group laws, graph relations, and light
cryptography-style modular statements.

The curated lane can add reviewed public theorem sets and benchmark-style
formalizations, including miniF2F-style olympiad problems, Putnam-style
problems, Mathlib-adjacent facts, and FormalMATH-style Lean statements when they
fit the pinned toolchain.

Difficulty should increase concretely as the network scales:

- more theorem families and fewer repeated proof shapes;
- longer induction proofs and multi-step rewrites;
- harder Mathlib lemma selection;
- stronger quantifier and predicate reasoning;
- more abstract algebraic structures;
- larger finite set and combinatorics arguments;
- harder real-number inequalities and continuity facts;
- eventually, formalized statements connected to known open problems.

The point is not to hide the tasks. The point is to keep expanding public,
deterministic, verifiable theorem work.

---

## Harder and open work

Lemma should not begin by asking miners to solve the hardest open problems in
the world. A subnet needs a healthy proving loop first: miners need tasks they
can solve, validators need predictable verification, and the network needs a
record of valid work.

Once that base loop is healthy, Lemma can aim at harder targets. For open or
especially difficult formalized statements, the reward shape can be
winner-take-all: the first miner to resolve the published target through a
formally verified proof earns the reward.

Some famous problems may require careful formalization before proof rewards are
fair. A Lean statement can be valid while failing to capture the real informal
problem. For major targets, the statement itself may need review before the
subnet points rewards at it.

---

## Operating direction

The near-term operator goal is plain:

- a miner can run the AI proof path without bespoke support;
- a validator can publish theorem challenges, verify proof files, and set
  weights reliably;
- problem supply changes are tied to published registry hashes;
- public dashboards explain what passed without leaking private proof exports;
- changes to incentives preserve the binary Lean verification gate.

Under load, the practical work is queueing, timeouts, verification cost,
observability, and runbooks for stuck verifies, RPC drift, or bad releases.

---

## Through-line

**Lemma's identity is incentivized theorem proving; Lean verification stays the
objective floor.** Everything else exists to make that floor useful, fair, and
sustainable on a decentralized network.

---

## Related docs

| Doc | Use |
| --- | --- |
| [Architecture](architecture.md) | Components and data flow today. |
| [Governance](governance.md) | Pins, meta, policy. |
| [Objective decision](objective-decision.md) | One-sentence objective and scoring boundary. |
| [Proof verification incentives](proof-verification-incentives.md) | Proof-only reward design. |
| [Problem supply policy](problem-supply-policy.md) | Public generated supply boundary and builder promotion checklist. |
| [Open problem campaigns](open-problem-campaigns.md) | Future work for faithful open-problem formalization and harder proof rewards. |
| [Miner](miner.md) / [Validator](validator.md) | Install, keys, config, registration, and runtime commands. |
