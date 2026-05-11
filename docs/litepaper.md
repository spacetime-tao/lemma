# Lemma Litepaper

**Lemma** is a [Bittensor](https://docs.learnbittensor.org/) subnet. Miners answer published math statements with Lean proof scripts; validators run the same Lean check so everyone shares one pass-or-fail result before any scoring.

This is the core idea:

> Lemma rewards Lean-valid proofs for published theorem statements.

Everything else should support that rule.

## The Short Version

A **theorem** is a precise math claim. A **proof script** is Lean source code that closes that claim. **Lean** is a proof assistant: software that checks each inference mechanically, like a strict compiler for math.

On Bittensor, Lemma follows this loop:

1. The subnet publishes a theorem statement.
2. Miners use models, tools, and compute to search for a proof.
3. Miners return a `proof_script`.
4. Validators run Lean on the submission.
5. If Lean passes, the work can earn score; if it fails, there is nothing to score yet.

That makes Lemma **proof mining** in the same loose sense as Bitcoin mining: there, each round goes to whoever publishes the next valid block first; here, miners seek Lean-valid proofs that match the published theorem.

## Concrete examples (illustrative)

These are simplified for readability. Live challenges follow the same pattern—a
published formal statement, a miner-authored proof artifact, a mechanical check—but
real tasks pin imports, namespaces, and theorem names to whatever the subnet
published for that round.

### Example A: a small fact about natural numbers

**Theorem (plain English).** For any natural number \(n\), adding zero on the
right leaves \(n\) unchanged: \(n + 0 = n\). The walk-through below also picks a
concrete numeral, \(7 + 0 = 7\), as the final claim.

**What the subnet publishes.** A formal Lean version of that claim (plus pinned
toolchain and Mathlib revision). Everyone aims at the same target: close the
exact statement the broadcast names, in the module layout the rules require.

**What the miner returns.** A `proof_script`—Lean source, usually a
`Submission.lean`-style file that the challenge specifies.

**A real proof (illustrative).** The snippet below is valid Lean 4
(prelude-style). A **lemma** states the general fact; a **theorem** reuses that
lemma for a specific number. On the network, names, namespaces, and imports
come from the live challenge, not from this copy-paste.

```lean
/-- Adding zero on the right does not change a natural (helper lemma). -/
lemma add_right_zero (n : Nat) : n + 0 = n :=
  Nat.add_zero n

/-- Therefore 7 + 0 = 7, by the same fact. -/
theorem seven_add_zero : 7 + 0 = 7 :=
  add_right_zero 7
```

**How to read it.** `Nat.add_zero` is Lean’s standard lemma that \(n + 0 = n\).
The helper packages it under `add_right_zero`. The theorem applies the helper
with `n := 7`. Lean checks each step; if anything failed—wrong statement,
missing piece, or `sorry`—the file would not build.

### Example B: when no proof score is earned

**Same rule.** The subnet publishes a formal statement; the miner must return a
proof script that Lean accepts for **that** statement under policy.

**Mechanical failure.** Typical causes are unfinished proofs (`sorry`), unsolved
goals, syntax or import errors, wrong theorem name or statement relative to the
broadcast, or toolchain mismatch—not “almost correct” prose, because the
artifact is code, not an explanation.

**Outcome.** Lean rejects the build or leaves a goal open. That submission does
not earn proof score for that round: there is nothing to score until Lean
accepts a complete proof.

## Verification and rewards

The live path stays narrow so validators stay aligned:

- Publish the formal statement.
- Receive a proof script.
- Lean passes or fails under the pinned toolchain.

Lemma does **not** grade natural-language write-ups as the on-chain signal. Essays and chat logs can help people debug or teach; they are not what validators check for rewards.

If Lean accepts the script under policy, the verification pass is real. Length and readability can vary.

After that gate, Bittensor handles token economics the usual way: validators publish scores for miners (weights), and payouts follow subnet rules (alpha). Those scoring rules can change with governance; they should not replace or blur the Lean check.

Lemma separates two questions: whether the proof is valid (Lean answers that), and how valid work becomes weights (subnet policy). Extra signals belong in research until the subnet explicitly adopts them with evidence.

## What Miners Do

A miner exposes a network endpoint so validators can send theorem challenges. Bittensor calls that endpoint an **Axon**. When a challenge arrives, the miner tries to produce a Lean `proof_script`.

The reference miner uses a prover model through an OpenAI-compatible API (Chutes, OpenAI, Gemini’s compatible endpoint, Anthropic with optional extras, or another gateway). The reward-critical artifact is the proof script, not an essay.

Optional local Lean runs can catch mistakes early; the validator’s check is what matters for live scoring.

## What Validators Do

A validator sends challenges to miners, waits for responses, verifies each proof with Lean, turns results into scores, and writes scores on chain. Production validators typically run Lean in Docker; the sandbox image pins the toolchain and Mathlib revision so checks match across machines.

Validators follow subnet epoch timing: each round includes time for miners to respond and time for Lean to finish.

Transport details (how messages move on the wire) are in **Transport** below.

## Proofs, Scores, And Weights

The live rule is intentionally simple:

- Lean passes: the proof can enter scoring.
- Lean fails: the proof cannot receive proof score.

After Lean passes, Lemma turns eligible miner entries into **weights** (on-chain credit). Each verified proof starts from the same base score; proof length, style, and elegance do not change that base.

Reputation and credibility settings may adjust entries. **Same-coldkey partitioning** splits one coldkey’s allocation across its hotkeys so running many hotkeys under one coldkey does not multiply share by accident. It does not prove unique humans. Someone can still register many coldkeys if economics allow it.

## Problem Supply

The default live-style problem source is generated templates. A chain-aligned
seed maps to a generated theorem id such as `gen/<seed>`.

This map is public and deterministic. That is a known tradeoff, not a secret
evaluation system. Miners may learn repeated shapes over time.

The fix is better supply, not pretending the generator is hidden:

- add more varied generated builders;
- coordinate registry upgrades;
- measure solve and verify time;
- later add curated or bounty lanes for harder work.

There is also a frozen catalog mode for development and evaluation. It is gated
on purpose and is not the default production-style source.

## Models And APIs

Validators do not need an inference model to check proofs. They need the pinned
Lean sandbox and the shared validator profile.

Miners need a prover. The repo's prover path expects an API that can return a
full `Submission.lean` proof script.

Model choice is an operator decision. The important question is simple: does the
model produce proofs that pass Lean inside the validator's time window?

## Transport

Validators send challenges; miners listen on their server. Today that rides Bittensor’s client/server helpers: historically **Dendrite** on the validator side and **Axon** on the miner side. The payload type is `LemmaChallenge`. Responses include body-hash checks; validators drop replies when required hash data is missing or mismatched.

A future move to plain HTTP plus different signing would be a large migration, not a small toggle.

## Safety And Operations

Operators should treat keys carefully.

Coldkeys should stay local or offline. Hotkeys can run on VPS hosts. A miner or
validator service should not need the coldkey private file on the server.

Validators also need reliable Docker and Lean caches. A cold Lean workspace can
be much slower than a warm one. Production validators should use persistent cache
directories, pinned images, and realistic Linux hardware before drawing timing
conclusions.

Remote Lean workers can move CPU load off the validator host, but they add
network and auth concerns. Use private networking, bearer auth, and TLS when
crossing untrusted networks.

The practical operator goal is simple: keep services reachable, keep keys safe,
keep caches warm, and keep validators on the same published profile. A local
proof pass is useful, but live operation also needs miner forwards, validator
verification, `set_weights`, and repeated rounds on the actual subnet.

## Data And Exports

Lemma does not maintain a central public proof database by default.

Validators can write local JSONL exports for research or operations. A `summary`
profile avoids proof text and reward weights. A `full` profile can include proof
scripts, labels, proof metrics, and final weight data for private analysis.

Full exports can leak useful training and gaming signals. Keep them private
unless they have been reviewed and processed for release.

## Optional Mechanisms

Extra mechanisms exist for edge cases and governance experiments; they do not replace the Lean gate:

- **Commit-reveal** reduces certain cheating patterns by committing to a proof hash before sending the full script, at the cost of more round trips.
- **Miner verify attest** lets a miner sign that it ran local Lean—useful for audits, not hardware attestation.
- **Validator profile peer attest** helps a group of validators confirm they run the same policy fingerprint.
- **Proof intrinsic metrics** are research-only and do not drive live rewards.

## Codebase Map

Use this when you already know what Lemma does and need to find code:

- `lemma/protocol.py` — challenge synapse types.
- `lemma/problems/` — generated and catalog problem sources.
- `lemma/miner/` — reference miner and prover path.
- `lemma/validator/` — validator round flow.
- `lemma/lean/` — Lean workspaces and verification.
- `lemma/scoring/` — from eligible proofs to weights.
- `lemma/cli/` — supported `lemma` commands.
- `tools/` and `scripts/` — analysis, catalog work, CI.

Broader docs: this file for overview, [getting-started.md](getting-started.md) to run, [technical-reference.md](technical-reference.md) for behavior detail. Decision docs explain major choices.

## Current Status

Lemma is still proof-of-concept software, but it can run on Bittensor testnet:

- Network: `test`
- Subnet: `467`
- Mainnet name: Finney

The near-term goal is not a complicated reward theory. It is a reliable loop:
publish theorem, get proof, verify proof, score passing proofs, and operate the
subnet without special hand-holding.

## Roadmap

The first lane is steady generated work with predictable verification cost.

Later lanes can add curated theorem sets, Mathlib gaps, or submit-when-ready
bounties. Those lanes should still use public statements, pinned toolchains,
clear reward rules, and reproducible verification.

Long term, Lemma should become a market for verified mathematical progress. The
first step is keeping the basic rule clear and hard to fake.

## Start Here

To run Lemma, go to [getting-started.md](getting-started.md).

For deeper behavior details, use
[technical-reference.md](technical-reference.md).

Lay questions and quick answers: [faq.md](faq.md).
