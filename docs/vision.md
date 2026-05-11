# Vision

Lemma is a Bittensor subnet for formal math proofs.

Miners submit Lean proof scripts. Validators check those scripts in Docker.
Weights should center on Lean-verified proofs.

Objective:

> Lemma rewards Lean-valid proofs for published theorem statements.

Related:

- [objective-decision.md](objective-decision.md)
- [proof-verification-incentives.md](proof-verification-incentives.md)

## What Lemma Produces

Lemma produces verified theorem/proof pairs.

The subnet publishes a theorem. Miners search for a proof. Validators check the
proof. If Lean accepts it, the theorem/proof pair is valid work.

This is proof mining: Bitcoin miners produce valid hashes; Lemma miners produce
valid Lean proofs.

## Why Lean Is The Gate

Lean gives a mechanical check.

The proof either typechecks against the stated theorem, or it does not.

That gives Lemma a clear reward floor. The grader is not a human curve. It is
the Lean checker.

The tradeoff is discipline:

- the theorem statement must be fixed;
- the proof must be the editable surface;
- tooling must reject `sorry`, bad `axiom`s, and goal changes.

## Current State

The repo already runs an end-to-end loop:

1. choose or generate a problem;
2. send a `LemmaChallenge`;
3. run a prover;
4. verify with Lean;
5. participate in miner and validator flows.

Near-term bar: a new miner can join from docs, use known-formalized problems,
and get consistent scoring without special help.

## Bounty Lane Later

A future v1 lane can support slower work:

- hard curated statements;
- Mathlib gaps;
- `sorry` cleanup;
- submit-when-ready proofs;
- higher-stakes bounties.

This is not needed at launch.

The author of a proof can be a model, a person, or a team. Lean only checks the
final proof script against the locked theorem.

## Roadmap

### 1. v0 Economy

Launch with one steady generated lane.

Keep the rules simple:

- publish work;
- verify work mechanically;
- pay for valid work.

Validators and miners should be able to explain payouts in one page.

### 2. Security Around Lean

Lean is strict. The surrounding system must stay honest:

- lock statements;
- reject `sorry` and unsafe axioms;
- pin Docker images and toolchains;
- publish profile hashes;
- document upgrade paths.

Goal: a short threat model and a validator checklist that match production.

### 3. Problem Supply

A live subnet needs a governed problem feed.

Each live challenge should have:

- known class;
- expected verify cost;
- clear rotation policy.

Generated tasks are the first lane. Curated and bounty lanes can come later.

### 4. Scale And Operations

The subnet needs runbooks for:

- queues;
- timeouts;
- Lean cost;
- RPC drift;
- bad releases;
- stuck verify workers.

Goal: the subnet survives real miner load without manual firefighting.

### 5. Later Incentives

After real traffic, consider partial-progress tracks, lemma-submission tracks,
or anti-collusion changes.

Only add them when the reward can stay clear and testable.

## Through Line

Lemma's identity is paid theorem proving.

Lean verification stays the objective floor. Economics, problem supply, and
operations exist to make that floor useful, fair, and sustainable.

## Related Docs

| Doc | Use |
| --- | --- |
| [Architecture](architecture.md) | Components and data flow. |
| [Governance](governance.md) | Pins and release policy. |
| [Problem supply policy](problem-supply-policy.md) | Generated supply boundary. |
| [Open problem campaigns](open-problem-campaigns.md) | Long-term bounty lane. |
| [Getting started](getting-started.md) | Install and first commands. |
| [Miner](miner.md) / [Validator](validator.md) | Operator detail. |
