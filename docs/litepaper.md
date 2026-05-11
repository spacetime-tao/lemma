# Lemma Litepaper

**Lemma** is a **subnet** on [Bittensor](https://docs.learnbittensor.org/)—a network with its own incentive rules layered on the shared chain. It rewards **formal proofs**: miners answer published math statements with **Lean** proof scripts; **validators** rerun **Lean** so everyone agrees pass/fail before scoring.

This is the core idea:

> Lemma rewards Lean-valid proofs for published theorem statements.

Everything else should support that rule.

## The Short Version

A **theorem** is a precise math claim. A **proof script** is **Lean** source code that closes that claim. **Lean** is a **proof assistant**: software that checks each inference mechanically—like a strict compiler for math.

Lemma wires that into Bittensor:

1. The subnet publishes a theorem statement.
2. Miners use models, tools, and compute to search for a proof.
3. Miners return a `proof_script`.
4. Validators run Lean against the submitted proof.
5. Passing proofs can receive score.
6. Failing proofs receive no proof score.

That makes Lemma **proof mining** in the same broad sense as Bitcoin **mining**: there, miners seek hashes under a difficulty rule; here, miners seek **Lean-valid proofs** under a theorem rule.

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

## What Lemma Is Not

The live path is **machine-checked**: publish statement → proof script → Lean
pass or fail → scoring maps passes into **weights** (validator-assigned credit)
and **alpha** (the subnet token). Lemma does **not** grade natural-language
write-ups as the live reward signal.

Useful checks:

- Was the theorem exactly the one the subnet published?
- Did the miner return a proof script?
- Did Lean accept it under the pinned toolchain and policy?
- Do this subnet’s scoring rules count that pass toward rewards?

That narrow pipeline keeps verification repeatable across validators.

## Why Lean Matters

Lean gives Lemma a single, shared gate: the proof either typechecks against the
published theorem under the rules or it does not. **Rewards** for miners flow from
Bittensor’s weight-and-token machinery **after** that gate—based on the proof
script, not on off-chain opinion about how the math “ought to” be argued.

Explanations, chat logs, and heuristics can help people **debug** or **teach**,
but they are not the on-chain pass/fail check. Proof length, style, and
readability can vary; if Lean accepts the script, the pass is real. Any extra
signals belong in research or out-of-band analysis until the subnet explicitly
adopts them with evidence.

## What Miners Do

A miner runs an **Axon**—Bittensor’s name for the **server endpoint** the miner
exposes so validators can deliver challenges. When a validator sends a challenge,
the miner tries to produce a Lean proof script.

The reference miner uses a prover model through an OpenAI-compatible API. That
could be Chutes, OpenAI, Gemini through its OpenAI-compatible endpoint, Anthropic
with the optional extra, or another compatible gateway.

The miner's job is not to write an essay. Its reward-critical answer is
`proof_script`.

Miners can also run local Lean verification before answering. That can catch bad
proofs early, but the validator's check is still the one that matters for live
scoring.

## What Validators Do

A validator sends theorem challenges to miners (using Bittensor’s request path—
historically **Dendrite** on the validator side talking to the miner’s **Axon**),
waits for responses, checks each proof with Lean, scores eligible proofs, and
writes **weights** on chain. **Weights** are how validators say how much credit
each miner deserves; those feed into **alpha** payouts per Bittensor rules.

Production validators use Docker for Lean verification. The sandbox image pins
the Lean toolchain and Mathlib revision so validators check proofs the same way.

Validators wait for subnet epoch boundaries. Each round has a forward wait for
miner responses and a Lean timeout for proof checking.

## Proofs, Scores, And Weights

The live rule is intentionally simple:

- Lean passes: the proof can enter scoring.
- Lean fails: the proof cannot receive proof score.

After Lean passes, Lemma turns eligible miner entries into **weights**
(on-chain credit scores for miners).
Reputation/credibility policy may adjust a miner's entry. Same-coldkey
partitioning may split one coldkey's allocation across its successful hotkeys.
Proof length, style, and elegance do not change the live proof score.

Same-coldkey partitioning means one operator cannot multiply one coldkey's
allocation just by running many hotkeys under it. It does not prove unique human
identity. An attacker can still use many coldkeys if registration cost and subnet
economics make that worthwhile.

This means Lemma separates two questions:

- Is this submitted proof valid?
- How should valid work become weights?

The first question is mechanical. Lean answers it. The second question is subnet
policy. That policy can evolve, but it should not muddy the proof gate.

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

Lemma currently uses Bittensor’s **Dendrite → Axon** path: roughly speaking,
**validators send** challenges (**Dendrite** client) and **miners receive** them
on their **Axon** server. The payload type is `LemmaChallenge`.

The synapse includes body-hash integrity checks. Validators drop responses when
required hash data is missing or does not match.

Future subnet designs may move toward HTTP plus Epistula signing, but that would
be a major migration. It is not a small config switch.

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

Some mechanisms are available but not the main story:

- Commit-reveal can bind a miner to a proof before reveal, at the cost of more
  round trips.
- Miner verify attest lets a miner sign that it ran local Lean, but it is not
  hardware attestation.
- Validator profile peer attest helps a known validator group check that profile
  hashes match.
- Proof intrinsic metrics are research-only and do not drive live rewards.

These tools should not blur the core rule: the live path starts with Lean proof
verification.

## Codebase Map

The main repo owns both consensus-critical behavior and the supported operator
command surface.

- `lemma/protocol.py` defines the challenge synapse.
- `lemma/problems/` defines generated and catalog problem sources.
- `lemma/miner/` contains the reference miner and prover path.
- `lemma/validator/` contains the validator round flow.
- `lemma/lean/` builds Lean workspaces and runs verification.
- `lemma/scoring/` turns eligible proofs into weights.
- `lemma/cli/` keeps the supported `lemma` command surface.
- `tools/` and `scripts/` support analysis, catalog work, and CI checks.

The docs are split by use. This litepaper gives the overview.
`getting-started.md` is the action path. `technical-reference.md` is the deep
behavior reference. Decision docs record why important choices were made.

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
