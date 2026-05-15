# Lemma Proof Protocol

Lemma is a Lean proof-verification protocol on a Bittensor subnet.

The protocol is intentionally small: validators publish one formal theorem
target, miners commit before reveal, miners later return Lean proof files, and
validators run Lean. The reward object is the verified proof, not a written
explanation about the proof.

## Target Supply

Targets come from a vendored known-theorem manifest:

- fixed source snapshot;
- fixed Lean toolchain and Mathlib revision;
- deterministic `order`;
- human proof reference;
- attribution, duplicate-review notes, and statement-faithfulness notes;
- fixed `Challenge.lean` and `Submission.lean` skeleton.

The current manifest is a Mathlib-only smoke queue. Replace it with reviewed
launch-quality targets before live use.

## Active Target

Validators compute the active target as:

```text
first manifest target without a matching solved-ledger row
```

The chain seed still controls validator timing, but it does not randomize the
target. Everyone works down the same list.

A solved-ledger row only matches when both the target id and theorem statement
hash match the current manifest. Stale rows from an older target definition do
not advance the queue or keep weights alive.

The first target starts at `LEMMA_TARGET_GENESIS_BLOCK`. Each next target starts
at the previous target's accepted block plus one. The commit window lasts
`LEMMA_COMMIT_WINDOW_BLOCKS` blocks, default `25`; reveal opens at the next
block.

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

The Axon miner daemon is one transport for the reveal. A portal can also host
wallet-submitted proof packages for registered miner hotkeys. In that path, the
browser still publishes the same compact commitment from the miner hotkey, the
portal verifies and stores the proof privately, and validators configured with
`LEMMA_PORTAL_CANDIDATES_URL` fetch candidates after reveal. Validators do not
trust the portal as a grader: they map the hotkey to a UID, verify the hotkey
signature, re-check the on-chain commitment, dedupe against Axon responses, and
run Lean before writing the solved ledger.

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

The static public dashboard export turns accepted proofs into replay receipts:
target fingerprint, validator hotkey, solver UID/hotkey, proof hash, nonce,
commitment hash/timing, and `proof_script`. Pending miner submissions stay
local; accepted proofs are public so third parties can rerun Lean.

## Rewards

Before the first solved target, validators write no miner weights.

After a solve, the current verified solver set receives miner weight until the
next target is solved. Among all revealed proofs that pass Lean and have valid
pre-cutoff commitments, the earliest valid commitment block wins. If multiple
valid solvers committed in that same block, those UIDs split the weight equally.

Duplicate submissions for an already-solved target do not change rewards.

Difficulty labels are operator planning metadata. They do not change reward
weight.

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

## Launch Note

Run Lemma on a fresh or intentionally reset subnet state. Stale weights from old
mechanisms should not carry into the proof protocol.
