# What Is Lemma?

Lemma is a Bittensor subnet for Lean-verified proof discovery and public proof publication.

It publishes exact Lean theorem statements. Miners compete to produce proof files. Validators check those proof files with Lean. Passing proofs become eligible for rewards under the subnet rules.

In Bittensor terms, miners produce work and validators measure it. In Lemma, the work is a Lean proof and the measurement is deterministic verification.

## Why Formal Proofs?

Formal proofs give the network a crisp correctness signal. A validator does not need to decide whether an explanation is persuasive. It checks whether Lean accepts the submitted proof for the exact target.

## What Is A Target?

A target is a published unit of work. It includes:

- a Lean theorem statement,
- imports and namespace context,
- the Lean and mathlib environment,
- a submission policy,
- source metadata,
- a target hash.

Most future targets should come from public Formal Conjectures statements. Lemma pins the selected source and turns it into a verifier-ready target.

## Who Participates?

Miners search for proofs and submit `Submission.lean` files.

Validators fetch the target registry, run the pinned verifier, and treat Lean acceptance as the correctness boundary.

Target curators select suitable public statements, pin source metadata, and keep candidate targets separate from live reward-backed targets.

The wider community can inspect target provenance and proof artifacts. When a solved target came from Formal Conjectures and has enough source metadata, Lemma can prepare an upstream PR candidate that links the artifact for normal upstream review.

## What Changed From Older Designs?

Lemma no longer needs recurring prompt rounds as its public product story. The durable loop is target publication, proof search, Lean verification, validator attestation, reward eligibility, public proof artifact, and upstream PR candidate.

## What Makes Lemma Useful?

Lemma rewards mechanically checked mathematical artifacts rather than plausible text. That makes it a useful proving ground for AI theorem proving, formalization tooling, upstream contribution candidates, and reproducible mathematical work.
