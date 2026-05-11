# Commit-Reveal Threat Model

`LEMMA_COMMIT_REVEAL_ENABLED=1` makes each challenge use two miner forwards.

1. Commit: miner returns `proof_commitment_hex`.
2. Reveal: miner returns the cached proof and `commit_reveal_nonce_hex`.

The validator accepts reveal only if the proof and nonce hash back to the stored
commitment for the same UID.

The commitment binds:

- protocol magic bytes;
- `theorem_id`;
- `metronome_id`;
- miner nonce;
- full proof script.

## What It Protects

Commit-reveal binds the miner to one proof before reveal.

The commit phase shows only a digest, not the proof text. The reveal phase later
shows the full proof.

## What It Does Not Protect

Commit-reveal is not a chain-anchored public fairness system.

It does not:

- prove the commit existed at a block;
- stop miners from precomputing public theorems;
- stop copied proofs;
- make validator scheduling trustless;
- stop validator/miner collusion;
- replace Lean verification;
- keep the proof private after reveal.

Both phases run inside one validator process in one epoch.

## Operator Guidance

Use commit-reveal when you want payload binding and can afford the extra round
trip.

Expect:

- about double axon round-trip work;
- reveal failures after miner restarts or cache expiry;
- `commit_reveal_rejects` in epoch logs for missing or bad reveals.

Stronger public fairness would need a separate design.
