# Commit-Reveal Threat Model

`LEMMA_COMMIT_REVEAL_ENABLED=1` turns each validator challenge into two miner
forwards:

1. `commit`: the miner solves the challenge and returns only
   `proof_commitment_hex`.
2. `reveal`: the miner returns the cached proof and `commit_reveal_nonce_hex`.

The validator keeps the commitment from phase 1 and accepts phase 2 only if the
revealed preimage hashes back to that commitment for the same UID. The preimage
binds:

- protocol magic bytes,
- `theorem_id`,
- `metronome_id`,
- 32-byte miner nonce,
- full proof script.

The miner-side cache is keyed by validator dendrite hotkey, theorem id, and
metronome id. It is TTL-bounded and size-bounded. If a miner restarts or the
entry expires before reveal, the reveal is rejected.

## What It Protects

Commit-reveal prevents a miner from publishing a commitment and then revealing a
different proof for that same challenge. It also means the commit phase does not
expose proof text to the validator or wire observers; only the digest is visible
until reveal.

In Lemma, this is useful as a narrow same-round binding check. It makes the
miner commit to one payload before the reveal response is scored.

## What It Does Not Protect

This is not a chain-anchored delayed commitment scheme.

It does not:

- prove to third parties that a commitment existed at a particular block,
- stop miners from precomputing public deterministic theorems,
- stop copied or shared proofs that existed before the commit phase,
- make the validator schedule or problem choice trustless,
- protect against validator/miner collusion,
- replace Lean verification, body-hash integrity, challenge-field binding, or
  miner verify attest,
- make the revealed proof private after the reveal phase.

Both phases are run by the same validator process in one epoch. That is a real
limit. Treat commit-reveal as optional payload binding, not as the core security
model of the subnet.

## Operator Guidance

Use commit-reveal when the extra round trip is acceptable and you want miners to
bind the proof before reveal. Leave it off when lower latency and simpler miner
state matter more.

If enabled, expect:

- roughly double axon round-trip latency per sub-round,
- reveal failures when miner cache entries expire or are lost,
- `commit_reveal_rejects` in epoch logs when commits are missing or reveal
  preimages do not match.

Changing the threat model from same-round binding to stronger public fairness
would need a different design, such as chain-anchored commitments or a
cross-validator protocol. That should be a separate product decision, not a
cleanup patch.
