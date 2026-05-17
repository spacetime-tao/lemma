# What Is Lemma?

Lemma is a Bittensor subnet for solving open mathematical conjectures from Google DeepMind's public `formal-conjectures` repository.

It turns selected Lean statements into proof bounties. Miners compete to produce proof files. Validators check those proof files with Lean. Passing proofs become eligible for rewards under the subnet rules, and solved work can become a public proof artifact plus an upstream pull request candidate.

In Bittensor terms, miners produce work and validators measure it. In Lemma, the work is a Lean proof and the measurement is deterministic verification.

## Plain English

Google DeepMind maintains a public repository of mathematical conjectures written in Lean. Lemma picks open statements from that repository and turns them into bounties.

Miners try to prove the theorem. Validators run Lean. If the proof builds, the solver can claim the bounty under Lemma's rules. Then Lemma publishes the proof and prepares a pull request back to Formal Conjectures so humans can review the result.

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

Most future targets should come from Google DeepMind Formal Conjectures statements. Lemma pins the selected source and turns it into a verifier-ready proof challenge.

## Who Participates?

Miners are proof searchers. They use AI systems, tactics, scripts, or human insight to find `Submission.lean` proofs.

Validators are proof checkers. They run the pinned verifier and attest only when Lean accepts the proof.

Lean is the judge. No essays, no subjective scoring, no vibes. The proof checks or it fails.

Target curators select suitable public statements, pin source metadata, and keep candidate targets separate from live reward-backed targets.

The wider community can inspect target provenance and proof artifacts. When a solved target came from Formal Conjectures and has enough source metadata, Lemma can prepare an upstream PR candidate that links the artifact for normal upstream review.

## What Changed From Older Designs?

Lemma no longer needs recurring prompt rounds as its public product story. The durable loop is target publication, proof search, Lean verification, validator attestation, reward eligibility, public proof artifact, and upstream PR candidate.

## What Makes Lemma Useful?

Lemma rewards mechanically checked mathematical artifacts rather than plausible text. That makes it a useful proving ground for AI theorem proving, formalization tooling, upstream contribution candidates, and reproducible mathematical work.

## Relationship To Google DeepMind

Lemma is independent and is not endorsed by Google DeepMind. It uses the public `google-deepmind/formal-conjectures` repository as target material. Upstream maintainers retain normal review authority over any pull requests Lemma prepares.
