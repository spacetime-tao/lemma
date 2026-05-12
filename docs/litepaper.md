# Lemma Litepaper

**Lemma** is a [Bittensor](https://docs.learnbittensor.org/) subnet for formal mathematical proof. Miners submit Lean proof scripts for published theorem statements. Validators run those scripts against the same pinned verifier, creating a shared mechanical gate before any scoring or reward policy applies.

The core rule is simple:

> Lemma rewards Lean-valid proofs for published theorem statements.

Everything else in the system exists to make that rule reliable, reproducible, and economically useful.

## The Short Version

A **theorem** is a precise mathematical claim. A **proof script** is Lean source code that proves that claim. **Lean** is a proof assistant: software that checks each inference step mechanically, like a strict compiler for mathematics.

A Lemma round works like this:

1. The subnet publishes a theorem statement.
2. Miners use models, tools, and compute to search for a proof.
3. Miners submit a `proof_script`.
4. Validators run Lean on the submission under the pinned toolchain.
5. Passing proofs become eligible for score; failing proofs are not.

In that limited sense, Lemma is a form of proof mining. Bitcoin miners compete to produce the next valid block. Lemma miners compete to produce Lean-valid proofs for published theorem statements. The analogy is useful, but the work and reward mechanics are different.

## Concrete Examples

The examples below are simplified for readability. Live challenges follow the same structure: a published formal statement, a miner-authored proof artifact, and a mechanical Lean check. Real rounds also pin imports, namespaces, theorem names, toolchain versions, and Mathlib revisions.

### Example A: a small fact about natural numbers

**Plain-English theorem.** For any natural number \(n\), adding zero on the right leaves \(n\) unchanged: \(n + 0 = n\). The example below also specializes that fact to the concrete statement \(7 + 0 = 7\).

**What the subnet publishes.** A formal Lean statement, together with the pinned toolchain and Mathlib revision. Everyone works against the same target: the exact theorem statement and module layout published for that round.

**What the miner returns.** A `proof_script`: Lean source code, usually in a
challenge-specified file such as `Submission.lean`.

**A real `Submission.lean` proof (illustrative).** The snippet below is a small
complete file. On the network, theorem names, namespaces, imports, and allowed
tactics come from the live challenge, not from this copy-paste.

```lean
import Mathlib

namespace Submission

theorem seven_add_zero : 7 + 0 = 7 :=
  by
    norm_num

end Submission
```

**How to read it.** The file imports Mathlib, uses the `Submission` namespace
expected by Lemma's checker, states the target theorem, and uses `norm_num` to
prove the arithmetic equality. Lean checks the file; if the statement is wrong,
the proof is incomplete, or the file uses a banned shortcut such as `sorry`, the
submission does not pass.

### Example B: when no proof score is earned

**Same rule.** The subnet publishes a formal statement; the miner must return a
proof script that Lean accepts for **that** statement under policy.

**Mechanical failure.** Typical causes are unfinished proofs (`sorry`), unsolved
goals, syntax or import errors, wrong theorem name or statement relative to the
broadcast, or toolchain mismatch—not “almost correct” prose, because the
artifact is code, not an explanation.

**Outcome.** Lean rejects the build or leaves a goal open. Until Lean accepts a complete proof of the published statement, that submission does not earn proof score.

## Verification and Rewards

The live verification path is intentionally narrow:

- the subnet publishes a formal theorem statement;
- miners submit proof scripts;
- validators run Lean under the pinned toolchain;
- Lean either accepts or rejects the submission.

Lemma does **not** use natural-language write-ups as the reward-critical artifact. Essays, chat logs, and explanations can help humans debug or learn, but validators reward proof scripts that pass the formal checker.

After Lean accepts a submission, Bittensor handles token economics in the usual way: validators publish miner scores, or weights, and payouts follow the subnet’s alpha reward rules. Those scoring rules can evolve through governance, but they should not blur the verification gate.

Lemma separates two questions:

1. **Is the proof valid?** Lean answers this.
2. **How does valid work become weight?** Lemma’s subnet policy answers this.

Extra signals, such as intrinsic proof metrics, should remain research-only until the subnet explicitly adopts them with evidence.

## What Miners Do

A miner exposes a network endpoint so validators can send theorem challenges. Bittensor calls that endpoint an **Axon**. When a challenge arrives, the miner searches for a Lean `proof_script` that closes the published theorem.

The reference miner uses a prover model through an OpenAI-compatible API, such as Chutes, OpenAI, Gemini’s compatible endpoint, Anthropic with optional extras, or another gateway. Operators may choose their own proving stack. The reward-critical artifact is always the proof script, not a prose explanation.

Running Lean locally can catch mistakes before submission, but the validator’s check is what matters for live scoring.

## What Validators Do

A validator sends challenges to miners, collects responses, verifies each proof with Lean, converts eligible results into scores, and writes those scores on chain.

Validator verification runs Lean **inside Docker**: `lemma validator start` expects Docker and the pinned sandbox image. That pins the toolchain and Mathlib revision so results match across machines.

Validators follow subnet epoch timing: each round includes time for miners to respond and time for Lean verification to finish. Transport details are covered below.

## Proofs, Scores, And Weights

The live rule is intentionally simple:

- **Lean passes:** the proof can enter scoring.
- **Lean fails:** the proof cannot receive proof score.

Once Lean accepts a submission, Lemma turns eligible miner entries into **weights**, the on-chain credit validators publish for miners. Each verified proof starts from the same base score. Proof length, style, and elegance do not change that base.

Reputation and credibility settings may adjust eligible entries. **Same-coldkey partitioning** splits one coldkey’s allocation across its hotkeys so running multiple hotkeys under one coldkey does not multiply share by accident. This reduces one easy form of overcounting, but it does not prove unique humans. A participant can still register many coldkeys if the economics allow it.

## Problem Supply

The default live-style problem source is generated templates. A chain-aligned seed maps deterministically to a generated theorem id such as `gen/<seed>`.

This mapping is public by design. It is a tradeoff, not a hidden evaluation system. Miners may learn repeated problem shapes over time.

The answer is better supply, not secrecy:

- add more varied generated builders;
- coordinate registry upgrades;
- measure solve and verify time;
- later add curated or bounty lanes for harder work.

A frozen catalog mode also exists for development and evaluation. It is gated intentionally and is not the default production-style source.

## Models and APIs

Validators do not need an inference model to check proofs. They need the pinned Lean sandbox and the shared validator profile.

Miners need a proving strategy. The reference prover path expects an API that can return a complete `Submission.lean` proof script.

Model choice is an operator decision. The practical question is simple: can the model produce proofs that pass Lean within the validator’s time window?

## Transport

Validators send challenges; miners listen for them. Today, Lemma uses Bittensor’s client/server helpers: historically **Dendrite** on the validator side and **Axon** on the miner side. The payload type is `LemmaChallenge`.

Responses include body-hash checks. Validators drop replies when required hash data is missing or mismatched.

Moving to plain HTTP plus a different signing model would be a major migration, not a small configuration change.

## Safety and Operations

Operators should treat keys carefully.

Coldkeys should stay local or offline. Hotkeys can run on VPS hosts. A miner or validator service should not need the coldkey private file on the server.

Validators also need reliable Docker and warm Lean caches. A cold Lean workspace can be much slower than a warm one. Production validators should use persistent cache directories, pinned images, and realistic Linux hardware before drawing timing conclusions.

Remote Lean workers can move CPU load away from the validator host, but they add network and authentication risks. Use private networking, bearer authentication, and TLS when crossing untrusted networks.

The practical operator goal is simple: keep services reachable, keep keys safe, keep caches warm, and keep validators on the same published profile. A local proof pass is useful, but live operation also requires miner connectivity, validator verification, `set_weights`, and repeated rounds on the actual subnet.

## Data and Exports

Lemma does not maintain a central public proof database by default.

Validators can write local JSONL exports for research or operations. A `summary` profile avoids proof text and reward weights. A `full` profile can include proof scripts, labels, proof metrics, and final weight data for private analysis.

Full exports may leak useful training or gaming signals. Keep them private unless they have been reviewed and processed for release.

## Optional Mechanisms

Several optional mechanisms exist for edge cases and governance experiments. None of them replaces the Lean verification gate:

- **Commit-reveal** reduces certain cheating patterns by committing to a proof hash before sending the full script, at the cost of more round trips.
- **Miner verify attest** lets a miner sign that it ran local Lean. This is useful for audits, but it is not hardware attestation.
- **Validator profile peer attest** helps a group of validators confirm they are running the same policy fingerprint.
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

Lemma is proof-of-concept software that can run on Bittensor testnet:

- Network: `test`
- Subnet: `467`
- Mainnet name: Finney

The near-term goal is a reliable loop: publish theorem, receive proof, verify proof, score passing proofs, and operate the subnet without special hand-holding.

## Roadmap

The first lane is steady generated work with predictable verification cost.

Later lanes can add curated theorem sets, Mathlib gaps, or submit-when-ready bounties. Those lanes should still use public statements, pinned toolchains, clear reward rules, and reproducible verification.

Long term, Lemma should become a market for verified mathematical progress. The first step is keeping the basic rule clear, reproducible, and hard to fake.

## Start Here

To run Lemma, go to [getting-started.md](getting-started.md).

For deeper behavior details, use
[technical-reference.md](technical-reference.md).

Lay questions and quick answers: [faq.md](faq.md).
