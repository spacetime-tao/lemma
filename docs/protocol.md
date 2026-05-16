# Lemma Proof Protocol

Lemma is a Lean proof-verification protocol on a Bittensor subnet.

The protocol is intentionally small: validators publish one formal theorem
target, miners commit before reveal, miners later return Lean proof files, and
validators run Lean. The reward object is the verified proof, not a written
explanation about the proof.

## Target Supply

Cadence targets come from hybrid supply:

- a curated known-theorem manifest with a fixed source snapshot;
- deterministic generated cadence builders;
- fixed Lean toolchain and Mathlib revision;
- deterministic `order`;
- human proof reference;
- attribution, duplicate-review notes, and statement-faithfulness notes;
- fixed `Challenge.lean` and `Submission.lean` skeleton.

The curated manifest is still reviewed before live use. Generated builder order
is append-only.

## Active Target

Validators compute the cadence window from the current chain head:

```text
seed = floor(chain_head / 100) * 100
```

The default window is 100 blocks. Solved-ledger entries no longer advance the
next cadence task.

The public dashboard shows the anchor theorem for the previous, current, and
next windows. By default, each registered UID gets a deterministic same-split
variant derived from the window seed and UID. This makes copying less useful
without claiming Sybil-proof identity.

The commit window lasts `LEMMA_COMMIT_WINDOW_BLOCKS` blocks, default `25`,
inside each 100-block cadence window; reveal opens at the next block.

## Commit And Reveal

`lemma mine` verifies the proof locally, stores it in the miner submission
store, creates a random nonce, publishes a Bittensor metadata commitment, and
starts the miner server. The hidden `lemma submit` command remains available for
scripts that only want to verify and store a proof. The public metadata is the
compact `lemma:v1:<commitment-hash>` payload; it does not reveal proof text,
proof hash, target id, or nonce.

During commit phase, miners serve no proof text. During reveal phase, miners
return `proof_script`, nonce, and commitment hash for the exact active target.
Validators accept a response only when the on-chain payload at the commit cutoff
recomputes from:

- protocol domain;
- netuid;
- miner hotkey;
- manifest hash;
- target id;
- theorem statement hash;
- proof hash;
- nonce.

Late commitments, copied commitments under another hotkey, wrong target hashes,
wrong proof hashes, and wrong nonces are rejected before Lean verification.

The Axon miner daemon is the supported reveal transport. Browser solve-portal
submission code has been removed; miners work offline, commit on-chain, then
serve the proof to validators after reveal opens.

## Solved Ledger

The solved ledger is JSONL. Each accepted row records:

- target id;
- verified UIDs, hotkeys, and coldkeys when known;
- proof hashes;
- proof nonce, commitment hash, commitment first-seen block, and commitment
  cutoff block;
- accepted block and Unix time;
- validator hotkey;
- Lemma version;
- verifier reason and build seconds;
- theorem statement hash;
- accepted proof text when the validator has the verified proof response.

The operator-published ledger is the source of truth for solved targets.

The public cadence export is intentionally smaller than the solved ledger. It
shows task state, validator hotkey, solver UID, and full solver hotkey. It does
not publish proof text, proof hashes, nonces, or commitment hashes.

## Rewards

Each epoch updates per-UID rolling scores. Proof correctness is binary: Lean
passes or fails. Passing a cadence proof contributes a difficulty-weighted
positive outcome; failing contributes a zero outcome. Infrastructure failures do
not penalize miners.

```text
effective_alpha = 1 - (1 - alpha) ** difficulty_weight
```

Difficulty weights are `easy=1`, `medium=2`, `hard=4`, and `extreme=8`.
Positive rolling scores normalize into Bittensor weights. If there are no
positive rolling scores, validators skip `set_weights`.

Same-coldkey partitioning is default-on as work/reward pressure. It is not
Sybil-proof identity.

## Verification

Miners reveal `proof_script` plus the nonce after the commit window. The
verifier builds the bridge target `Solution`, so the submitted theorem must
match the locked statement. `sorry`, `admit`, new axioms, unsafe code, timeouts,
and mismatched theorem statements do not verify.

## Target Review

Before a launch target is eligible, the manifest row records:

- a human proof citation;
- best-effort duplicate search against the pinned Lean/mathlib snapshot;
- reviewer attestation that the theorem is known and not already accepted as a
  Lean proof;
- statement-faithfulness notes.

Formal Conjectures is useful target-discovery material, but `hasFormalProof=false`
only means the site has no external formal-proof reference. Source files still
need inspection because some simple `test` entries are already proved in-repo.

Formal Conjectures campaign tasks are manual operator-funded work, separate
from cadence validator weights. The repo keeps a campaign registry and
append-only acceptance ledger. The private acceptance ledger stores the winning
proof hash, hotkey, optional UID, and accepted time; the public bounty feed
publishes only the hotkey, optional UID, accepted time, and reward status.

## Launch Note

Run Lemma on a fresh or intentionally reset subnet state. Stale weights from old
mechanisms should not carry into the proof protocol.
