# Lemma Proof Protocol

Lemma is a Lean proof-verification protocol on a Bittensor subnet.

The protocol is intentionally small: validators publish one formal theorem
target, miners return Lean proof files, and validators run Lean. The reward
object is the verified proof, not a written explanation about the proof.

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
first manifest target whose id is not present in the solved ledger
```

The chain seed still controls validator timing, but it does not randomize the
target. Everyone works down the same list.

## Solved Ledger

The solved ledger is JSONL. Each accepted row records:

- target id;
- verified UIDs, hotkeys, and coldkeys when known;
- proof hashes;
- accepted block and Unix time;
- validator hotkey;
- Lemma version;
- verifier reason and build seconds;
- theorem statement hash.

The operator-published ledger is the source of truth for solved targets.

## Rewards

Before the first solved target, validators write no miner weights.

After a solve, the current verified solver set receives miner weight until the
next target is solved. A single valid solver receives the full weight. If more
than one miner verifies in the same validator batch, those UIDs split the weight
equally.

Duplicate submissions for an already-solved target do not change rewards.

Difficulty labels are operator planning metadata. They do not change reward
weight.

## Verification

Miners submit only `proof_script`. The verifier builds the bridge target
`Solution`, so the submitted theorem must match the locked statement. `sorry`,
`admit`, new axioms, unsafe code, timeouts, and mismatched theorem statements do
not verify.

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
