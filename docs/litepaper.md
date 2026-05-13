# Lemma Litepaper

**Lemma is a Bittensor subnet that rewards correct mathematical proofs.**

Every round, Lemma posts a theorem written in Lean. Miners run automated proving
systems. Validators run Lean. The proof passes or it fails.

Bitcoin rewards miners for securing the network. Bittensor rewards miners for
producing useful intelligence. Lemma rewards miners for producing correct
proofs. The work is different, but the pattern is familiar: open participants
compete under public rules, and the network rewards work that can be checked.

## The Short Version

A theorem is a precise mathematical claim. A proof is a correct argument for
that claim. On Lemma, the proof is written as Lean code so software can check it
line by line.

A Lemma round works like this:

1. The subnet publishes a theorem statement.
2. Miners run an automated prover, usually an AI model plus a proof-search or
   repair loop.
3. Miners submit a `proof_script`.
4. Validators run Lean under the pinned toolchain.
5. Passing proofs can enter scoring; failing proofs cannot.

There is no reward-critical essay and no subjective grader. The artifact is proof
code. Lean accepts it, or Lean rejects it.

## Why Proofs?

Mathematics is one of the foundations under science, cryptography, algorithms,
software, physics, engineering, and AI reasoning. Better theorem proving can
produce solved problems, stronger reasoning systems, new training data, and a
public record of machine-checkable mathematical work.

Lemma does not need a revenue story to matter. Its value is the work it
coordinates: verified mathematical progress. How valuable that is should be
decided by the market, the same way markets decide how much they value Bitcoin's
security or Bittensor's intelligence.

## Why Lean?

Lean is a proof assistant: software for writing mathematics in a form computers
can check. Think of it like a strict compiler for proofs.

If a miner submits prose that sounds convincing, Lean does not care. If the Lean
file proves the exact theorem under the pinned rules, it passes. If it changes
the goal, leaves work unfinished, uses a banned shortcut such as `sorry`, or
does not type-check, it fails.

That mechanical gate is what makes the subnet credible. Validators do not need
to decide whose explanation sounded best. They run the checker.

## Why Bittensor?

Bittensor provides open miner participation, validator scoring, chain-visible
weights, and token rewards. Lemma uses that structure for a task with an
objective check.

The pairing is simple:

- Bittensor coordinates the network.
- Lean checks the work.
- Lemma points that market at theorem proving.

## What Counts As Work?

Anything that can be formalized as a Lean statement can become work for Lemma.
That includes algebra, number theory, logic, combinatorics, geometry, computer
science, cryptography, and other mathematical domains.

Lemma's scope is broad mathematics: start with a reliable proving loop, then
broaden the range and difficulty of theorem work as the network scales.

## Why Not Only Famous Unsolved Problems?

Starting with the hardest open problems would make the token nearly impossible
to earn and the subnet hard to bootstrap.

Bitcoin did not begin with today's difficulty. Lemma should also begin with a
base loop that lets miners build proof capacity, tooling, participation, and
validator reliability.

The long-term direction can still include difficult or unsolved mathematics. The
path is a ladder:

1. a reliable cadence of generated and curated theorem tasks;
2. broader theorem supply across more mathematical fields;
3. steadily harder formal statements as the network scales;
4. winner-take-all proof rewards for unsolved or especially difficult targets.

## Concrete Example

The examples below are simplified for readability. Live challenges follow the
same structure: a published formal statement, a miner-authored proof artifact,
and a mechanical Lean check.

### A Proof By Induction

Plain English: prove that the first `n` odd numbers add to `n ^ 2`.

A miner might submit this `Submission.lean` file:

```lean
import Mathlib

namespace Submission

theorem sum_first_odds (n : Nat) :
    (Finset.range n).sum (fun k => 2 * k + 1) = n ^ 2 :=
  by
    induction n with
    | zero =>
        simp
    | succ n ih =>
        rw [Finset.sum_range_succ, ih]
        ring

end Submission
```

This is still a compact example, but it shows the shape Lemma cares about:
a formal theorem, a proof strategy, and a final mechanical check. The proof uses
induction to handle every natural number, simplifies the zero case, rewrites the
successor case using the induction result, and lets Lean check the remaining
algebra. If the statement is wrong, the proof is incomplete, or the file uses a
banned shortcut, the proof fails.

### When No Score Is Earned

A submission does not earn proof score when Lean rejects it. Common reasons are
unfinished proofs, syntax errors, wrong theorem names, changing the target,
toolchain mismatch, or shortcut assumptions that the validator policy rejects.

There is no "almost correct" prose score in the live reward path.

## Rewards and Weights

The live verification rule is intentionally narrow:

- Lean passes: the proof can enter scoring.
- Lean fails: the proof cannot receive proof score.

After Lean accepts a submission, Lemma turns eligible miner entries into
weights, the on-chain credit validators publish for miners. Reputation,
credibility, and same-coldkey partitioning can adjust final allocation after
eligibility, but they do not replace the Lean verification gate.

Lemma separates two questions:

1. **Is the proof valid?** Lean answers this.
2. **How does valid work become weight?** Lemma's subnet policy answers this.

## What Miners Do

A miner runs automated prover software. When a theorem challenge arrives, the
miner sends the Lean statement to an AI proving model, a proof-search loop, a
repair loop, or some combination of those systems. If it finds a proof, it
returns a Lean `proof_script` for validators to check.

The reference miner uses a prover model through an OpenAI-compatible API, but
operators may use any proving strategy. The reward-critical artifact is always
the proof script, not the explanation of how it was found.

Running Lean locally can catch mistakes before submission. The validator's check
is what matters for live scoring.

## What Validators Do

A validator sends challenges to miners, collects responses, verifies each proof
with Lean, converts eligible results into scores, and writes those scores on
chain.

Validator verification runs Lean inside Docker using the pinned sandbox image.
That pins the toolchain and Mathlib revision so results match across machines.

## Problem Supply

The live-style problem source is hybrid: deterministically generated theorem
families plus a curated catalog lane. A chain-aligned seed maps deterministically
to a public theorem id such as `gen/<seed>` or `curated/...`.

Today the generated lane already covers natural-number arithmetic, finite sums,
induction, divisibility, modular arithmetic, primes, real polynomial identities,
real inequalities, continuity, absolute values, finite sets, set algebra, logic,
function composition, matrices, group laws, graph relations, and light
cryptography-style modular statements.

The curated lane can bring in reviewed public theorem sets and benchmark-style
formalizations, including miniF2F-style olympiad problems, Putnam-style
problems, Mathlib-adjacent facts, and FormalMATH-style Lean statements when they
fit the pinned toolchain.

Difficulty should increase concretely, not just by label. Good supply expansion
means adding statements that require longer induction arguments, more Mathlib
lemma selection, multi-step rewrites, stronger quantifier handling, more
abstract algebraic structures, harder real-number inequalities, larger finite
set arguments, and eventually formalized statements connected to known open
problems.

This mapping is public by design. The answer to repeated patterns is better
supply, not secrecy:

- add more varied generated builders;
- add reviewed curated catalog rows;
- coordinate supply registry upgrades;
- measure solve and verify time;
- later add winner-take-all proof rewards for especially difficult or unsolved
  targets.

## Transport and Operations

Validators send theorem challenges; miners return proof scripts. Bittensor
handles the signed miner/validator transport, while Lemma defines the challenge
payload and the Lean verification rule. Lower-level transport details are in
[technical-reference.md](technical-reference.md).

Operators should keep keys safe, services reachable, Docker healthy, and Lean
caches warm. Coldkeys should stay local or offline. Hotkeys can run on VPS hosts.
Remote Lean workers can move CPU load away from validators, but they require
private networking, authentication, and careful operation.

## Data and Exports

Lemma does not maintain a central public proof database by default.

Validators can write local JSONL exports for research or operations. A `summary`
profile avoids proof text and reward weights. A `full` profile can include proof
scripts, labels, proof metrics, and final weight data for private analysis.

Keep full exports private by default. They may include miner-submitted proof
scripts, solved examples, model labels, timing, and final weight data. Publishing
that raw data could reveal miner strategies or turn current theorem rounds into
training examples before the subnet is ready to release them.

## Why Now?

Formal mathematical reasoning is becoming a serious AI frontier. Recent work
shows models learning to search for Lean proofs, decompose proofs into useful
lemmas, and solve difficult competition-style mathematics. At the same time,
many mathematical problems remain unsolved, and some famous problem lists carry
large public rewards.

Useful references:

- [Olympiad-level formal mathematical reasoning with reinforcement learning](https://www.nature.com/articles/s41586-025-09833-y)
- [The Millennium Prize Problems](https://www.claymath.org/millennium-problems/)
- [Formal Theorem Proving by Rewarding LLMs to Decompose Proofs Hierarchically](https://arxiv.org/abs/2411.01829)
- [List of unsolved problems in mathematics](https://en.wikipedia.org/wiki/List_of_unsolved_problems_in_mathematics)
- [Lemma in mathematics](https://en.wikipedia.org/wiki/Lemma_(mathematics))

These links support the direction. They are not the mechanism. The mechanism is
still simple: publish theorem, verify proof, reward valid work.

## Current Status

Lemma is proof-of-concept software that can run on Bittensor testnet:

- Network: `test`
- Subnet: `467`
- Mainnet name: Finney

The near-term goal is a reliable loop: publish theorem, receive proof, verify
proof, score passing proofs, and operate the subnet without special
hand-holding.

## Roadmap

The first lane is steady generated and curated work with predictable
verification cost.

Later work can add broader theorem sets, Mathlib gaps, and winner-take-all proof
rewards for difficult or unsolved targets. Those targets should still use public
statements, pinned toolchains, clear reward rules, and reproducible
verification.

Long term, Lemma should become a market for verified mathematical progress. The
first step is keeping the basic rule clear, reproducible, and hard to fake.

## Start Here

To run Lemma, go to [getting-started.md](getting-started.md).

For deeper behavior details, use [technical-reference.md](technical-reference.md).

Plain questions and quick answers: [faq.md](faq.md).
