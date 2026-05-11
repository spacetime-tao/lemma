# Lemma Litepaper

Lemma is a Bittensor subnet for formal math proofs.

Miners submit Lean proof scripts for published theorem statements. Validators
check those scripts with Lean. A proof that passes can enter scoring. A proof
that fails cannot.

This is the core idea:

> Lemma rewards Lean-valid proofs for published theorem statements.

Everything else should support that rule.

## The Short Version

A theorem is a precise math claim. A proof script is Lean code that tries to
prove that claim. Lean is a proof assistant: it checks the proof mechanically.

Lemma turns that into a subnet:

1. The subnet publishes a theorem statement.
2. Miners use models, tools, and compute to search for a proof.
3. Miners return a `proof_script`.
4. Validators run Lean against the submitted proof.
5. Passing proofs can receive score.
6. Failing proofs receive no proof score.

That makes Lemma proof mining. Bitcoin miners produce valid hashes under a
difficulty rule. Lemma miners produce valid Lean proofs under a theorem rule.

## Concrete examples (illustrative)

These are simplified for readability. Live challenges follow the same pattern—a
published formal statement, a miner-authored proof artifact, a mechanical check—but
real tasks pin imports, namespaces, and theorem names to whatever the subnet
published for that round.

### Example A: a small arithmetic fact

**Theorem (plain English).** If \(a\) and \(b\) are even natural numbers, then
\(a + b\) is even.

**What the subnet publishes.** A formal Lean statement of that claim (plus pinned
toolchain and Mathlib revision). Everyone sees the same target: prove *this*
statement, not a paraphrase.

**What the miner returns.** A `proof_script`: Lean source that fills in the
proof—typically a complete `Submission.lean` module that imports what the
challenge requires and closes the theorem Lean expects.

**What “proof” means here.** It is not an essay and not a chat reply. It is code
Lean typechecks against the statement. Conceptually the miner fills in a proof
body for the exact theorem the validator broadcast—imports, namespace, and name
come from the live challenge rules. A toy shape (not a real challenge layout)
looks like:

```lean
-- Illustrative only — names/imports are dictated by the broadcast.
theorem published_claim : True := trivial
```

Real submissions replace `published_claim` and `True` with the actual statement
and a real proof script (`by …`) Lean accepts.

Validators do not grade style or elegance first—they check whether Lean accepts
the proof under policy.

### Example B: when no reward is earned

**Theorem (plain English).** Same published statement as above.

**Bad submission.** The miner returns a script that uses `sorry`, skips a goal,
imports the wrong module, or diverges from the published statement.

**Outcome.** Lean rejects the proof. That round cannot earn proof score from that
submission, regardless of how plausible the underlying idea sounds.

That separation—mechanical pass/fail before subjective judgment—is deliberate.

## What Lemma Is Not

Lemma is not a chat benchmark. It is not trying to reward the best explanation
of a proof. It is not asking validators to decide which answer sounds most
convincing.

The live reward path is narrower:

- Was the theorem the one the subnet published?
- Did the miner return a proof script?
- Did Lean accept that proof under the pinned toolchain and policy?
- Can that passing proof enter the weight map?

That narrowness is a feature. It makes the work easier to check, easier to
repeat, and harder to turn into subjective grading.

## Why Lean Matters

Lean gives Lemma a hard check. The proof either typechecks against the theorem or
it does not.

That matters because rewards should not depend on whether a person likes an
explanation. It should not depend on a model writing convincing prose. The live
reward path is about the proof script.

Informal reasoning can still be useful. It can help humans understand attempts,
debug model behavior, or build private datasets. It is not the live reward
signal.

The same distinction matters for proof length, style, and elegance. A short proof
may be good. A long proof may be good. A proof with awkward generated code may
still be valid. The live system starts with the fact that Lean accepted the proof.
Other research signals should stay out of the reward path until they have real
evidence behind them.

## What Miners Do

A miner runs a Bittensor Axon service. When a validator sends a challenge, the
miner tries to produce a Lean proof script.

The reference miner uses a prover model through an OpenAI-compatible API. That
could be Chutes, OpenAI, Gemini through its OpenAI-compatible endpoint, Anthropic
with the optional extra, or another compatible gateway.

The miner's job is not to write an essay. Its reward-critical answer is
`proof_script`.

Miners can also run local Lean verification before answering. That can catch bad
proofs early, but the validator's check is still the one that matters for live
scoring.

## What Validators Do

A validator sends theorem challenges to miners, waits for responses, checks each
proof with Lean, scores eligible proofs, and writes weights on chain.

Production validators use Docker for Lean verification. The sandbox image pins
the Lean toolchain and Mathlib revision so validators check proofs the same way.

Validators wait for subnet epoch boundaries. Each round has a forward wait for
miner responses and a Lean timeout for proof checking.

## Proofs, Scores, And Weights

The live rule is intentionally simple:

- Lean passes: the proof can enter scoring.
- Lean fails: the proof cannot receive proof score.

After Lean passes, Lemma turns eligible miner entries into weights.
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

Lemma currently uses Bittensor's Dendrite to Axon path. The synapse type is
`LemmaChallenge`.

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
