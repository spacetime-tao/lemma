# Lemma FAQ

Plain-language answers about Lemma, theorem proving, miners, validators, and why
verified reasoning matters.

## What is Lemma?

Lemma is a Bittensor subnet for using AI to prove mathematical theorems.

Lemma posts theorem challenges. Miners use AI systems to generate Lean proof
files. Validators check those files with Lean. If the proof is correct, it
passes. If it is incomplete, invalid, or changes the theorem, it fails.

Bitcoin rewards miners for securing a network. Bittensor rewards miners for
useful machine intelligence. Lemma rewards miners for producing correct,
machine-checkable proofs.

## How is this subnet useful?

Lemma creates a market for verified reasoning.

Most AI systems produce text that may sound convincing but can still be wrong.
Lemma focuses on a stricter kind of output: formal proofs that software can
check.

That is useful because it gives the network an objective way to reward correct
reasoning. Miners are not rewarded for persuasive answers, style, or claims.
They are rewarded for proof files that actually verify.

Over time, better AI theorem provers can support mathematics, software
verification, cryptography, algorithms, science, engineering, and other fields
where correctness matters.

## What do you mean by verified reasoning?

Verified reasoning means the answer can be checked by software, not just trusted
by humans.

In Lemma, miners submit proofs written in Lean. Lean checks whether every step
follows from the theorem statement, the allowed definitions, and the rules of
logic.

If the proof is valid, Lean accepts it. If even one required step is missing,
invalid, or based on an illegal shortcut, Lean rejects it.

So when Lemma says it rewards verified reasoning, it means miners are rewarded
for producing reasoning that survives an independent mechanical correctness
check.

## Why do miners solve math?

Miners solve math because formal proofs are one of the cleanest ways to measure
real AI reasoning.

A normal AI answer can be hard to judge. It might sound right while still being
wrong. A Lean proof is different: it either checks or it does not.

That makes theorem proving a good task for a subnet. Finding proofs can be hard,
creative, and compute-intensive. Checking them is objective and reproducible.

Miners are not solving math by hand. They run AI proving systems, search loops,
repair tools, and models that try to generate valid Lean proof files.

The goal is not "math for math's sake." The goal is to reward machines for
producing reasoning that can be independently verified.

## Who needs this math to be solved?

Some theorem challenges may be small on their own, but formal proofs can become
building blocks.

Mathematics supports cryptography, algorithms, physics, engineering, software,
machine learning, and scientific reasoning. Verified proofs can also become
training data, benchmarks, reusable formal-library contributions, and stepping
stones toward harder results.

That is why the name Lemma fits: in mathematics, a lemma is often a smaller
proven result used to prove something larger.

## Is Lemma only useful if it solves famous open problems?

No.

A subnet needs a reliable proving loop before it can aim at the hardest problems
in the world.

If every task is impossibly hard, miners get almost no feedback, validators have
few successful results to compare, and the subnet cannot produce a useful reward
signal. Lemma starts with theorem challenges that make the loop work: publish a
theorem, generate proofs, verify them, and reward valid work.

As miners improve, the theorem windows can become harder. Larger bounties and
harder curated problems can come later.

## Why not start with Millennium Prize Problems?

Because the first goal is to build proof capacity.

Millennium Prize Problems are among the hardest open problems in mathematics.
Starting there would give miners almost no feedback and validators almost no
useful reward signal.

Lemma starts with a working market for machine-checkable proofs. Once that
market becomes stronger, it can move toward harder problem sets and
longer-horizon bounties.

## What is formal mathematics?

Formal mathematics is mathematics written in a precise language that software
can check.

In ordinary math, a proof is usually written for humans. In formal math,
definitions, assumptions, and allowed reasoning steps are written explicitly
enough for a proof assistant to verify them.

Lemma uses this because it makes correctness objective. A validator does not
need to decide whether an explanation "seems right." It can run the proof
through Lean and see whether it verifies.

## What is Lean?

Lean is a proof assistant.

It lets people and AI systems write mathematical definitions, theorem
statements, and proofs in a formal language. Lean then checks whether the proof
is logically valid.

For Lemma, Lean acts like the judge. Miners submit proof files. Validators run
Lean. If Lean accepts the file under Lemma's rules, the proof is valid.

## What is a theorem?

A theorem is a precise claim that can be proven true.

In Lemma, theorem statements are written in Lean. This removes ambiguity. Every
miner receives a formal target, and validators check whether the submitted proof
proves that exact target.

## What is a proof?

A proof is a correct argument showing why a theorem is true.

In Lemma, a proof is not an essay. It is a Lean file. The file must contain code
that Lean can verify.

Human explanations can help people understand the proof, but the proof credit
comes from the Lean file itself.

## What does a proof assistant do?

A proof assistant checks whether a proof follows the rules of a formal system.

Lean verifies the proof step by step. If the reasoning is valid, the proof
passes. If something is missing, false, or unsupported, the proof fails.

This is similar to a compiler checking code, except the thing being checked is
mathematical reasoning.

## Why use Lean instead of normal text answers?

Because normal text answers are hard to score objectively.

A written explanation might look correct but hide a gap. A language model might
produce a fluent answer that is wrong. Different people may disagree about
whether an argument is detailed enough.

Lean gives Lemma a stricter standard. The proof must compile and verify.
Validators can run the same checker against the same theorem and proof file.

That makes rewards much harder to fake.

## What is a Bittensor subnet?

A Bittensor subnet is a specialized market for machine intelligence.

Each subnet defines the work it wants miners to perform, the rules validators
use to judge that work, and the reward signal that determines which miners earn.

Lemma's work is theorem proving. Miners try to produce Lean proofs. Validators
check those proofs. Correct proofs receive reward weight.

## What do miners do?

Miners receive theorem challenges and try to produce valid Lean proofs.

A miner may use language models, search algorithms, proof repair loops,
specialized provers, or other tools. The miner's job is to return a proof file
that passes validation.

Miners earn only when their submitted work satisfies the subnet's rules.

## Why do miners get different theorem variants?

Miners receive slightly different versions of a theorem during the same round.

This helps prevent simple copying while keeping the task fair. The variants are
deterministic, so validators know exactly which theorem each miner received and
check the submitted proof against that specific target.

The dashboard may show the public theorem window, but each miner's actual Lean
target can be a same-difficulty variant from that window.

## How long is a theorem round?

The default cadence round is 100 Bittensor blocks.

At roughly 12 seconds per block, that is about 20 minutes per theorem window.

The dashboard countdown shows the public window time. A miner request that
arrives late in the window may have less than the full 20 minutes before the
next theorem window begins.

## What do validators do?

Validators send theorem challenges to miners, collect their proof files, check
the submissions with Lean, reject invalid shortcuts, and publish reward weights.

Those weights tell Bittensor how rewards should be distributed among miners.

Validators are not grading opinions. They are checking whether submitted proof
files verify under the required rules.

## Are miners manually watching for theorems?

No. The reference miner is designed to run automatically.

It receives theorem challenges, calls an AI proving model or proof-search loop,
and returns a Lean file when it finds a candidate proof.

Humans may help design better miners, models, prompts, and search systems, but
the normal subnet loop is automated.

## What are bounties?

Bounties are escrow-backed proof rewards for harder targets that do not fit the
normal timed theorem rounds.

They are live only when funded in `LemmaBountyEscrow` on Bittensor EVM. Timed
rounds keep the subnet moving with regular challenges. Bounties are for selected
Lean statements that may need more time, stronger search, public review, or more
advanced proving systems.

Lemma uses Google DeepMind's public [Formal Conjectures](https://google-deepmind.github.io/formal-conjectures/)
database as the source of bounty targets. These are formal mathematical
statements that can be attempted in Lean.

The point of bounties is to give solvers a path toward harder, more meaningful
proofs while keeping the regular subnet loop simple and steady. A live claim
needs on-chain commit/reveal data, structured proof provenance, and a signed
binding between the miner hotkey and the EVM payout address. If escrow custody
is missing, the target is a draft or candidate, not an active reward.

Note: Lemma is not affiliated with or partnered with Google DeepMind.

## What rules do proof files follow?

Every submitted proof file must prove the exact theorem Lemma published. Miners
cannot change the theorem, add extra assumptions, use `sorry`, or add Lean
features that change the rules instead of proving the target.

Timed cadence tasks are intentionally strict. A cadence submission uses the exact
imports, opens `namespace Submission`, proves one exact target theorem, and ends
the namespace. Helper definitions and helper lemmas are not part of the cadence
default. Lean can support them in general, but Lemma keeps the timed loop narrow
because those rounds are frequent validator traffic and should be easy to check
the same way every time.

Said simply: cadence is about speed and time constraints. It is the fast,
regular loop where validators need to publish a theorem, collect answers, check
proofs, and move rewards without turning each round into a custom proof project.

Future bounties can be more flexible. A bounty proof may use helper definitions
and helper lemmas because harder proofs often need smaller pieces along the way.
Those helpers are still checked. They cannot change the target, add new
assumptions, add unsafe shortcuts, or bypass Lean's checker.

The same policy travels with local and remote verification, so a proof should
not pass locally under one set of rules and fail remotely under another.

## What are `sorry` and new axioms?

In Lean, `sorry` is a placeholder for an unfinished proof. It tells Lean to
temporarily accept a missing proof while someone is still working.

That is useful during development, but it is not a real proof. Lemma rejects
submissions that rely on `sorry`.

A new axiom is an extra assumption added by the submitted file. If miners could
add their own axioms, they could change the rules instead of proving the
theorem. Lemma rejects that too.

The point is simple: miners must prove the target, not bypass it.

## Can miners fake a proof?

They can try, but validators are designed to reject shortcuts.

A valid submission must prove the exact theorem under the allowed rules. If the
file changes the theorem, uses `sorry`, adds unsafe assumptions, or fails Lean's
checker, it should not earn proof credit.

This is why formal verification matters. The proof has to pass the checker, not
just look convincing.

## What are UID, weights, and alpha?

A UID is a numbered participant slot on a subnet.

Weights are validator-published reward signals. They tell Bittensor which
miners produced valuable work.

Alpha is the reward token for a Bittensor subnet.

Lemma currently runs on testnet, so public reward information should be treated
as test deployment data unless a mainnet deployment is announced.

## What is the difference between testnet and mainnet?

Testnet is for testing software, validator behavior, miner behavior, and subnet
design.

Mainnet, also called Finney, is the live Bittensor network where economic
rewards matter.

Lemma currently runs on testnet. Only rely on mainnet rewards if the Lemma
deployment you are following is registered, live, and configured for the correct
network and subnet ID.

## Where do I start?

If you want to understand the project, start with the [litepaper](litepaper.md).

If you want to participate, run a [miner](miner.md) or a
[validator](validator.md). Those pages include install, key, setup, and run
steps.

Miners compete to produce valid proofs. Validators check proofs and publish
reward weights. Both help test whether AI systems can produce verified reasoning
at scale.
