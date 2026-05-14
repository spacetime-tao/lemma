# Lemma WTA Protocol

Lemma’s live protocol is a small winner-take-all proof market.

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

## Solver Ledger

The ledger is JSONL. Each accepted row records:

- target id;
- winner UIDs, hotkeys, and coldkeys when known;
- proof hashes;
- accepted block and Unix time;
- validator hotkey;
- Lemma version;
- verifier reason and build seconds;
- theorem statement hash.

The operator-published ledger is the v1 source of truth for solved targets.

## Rewards

Before the first solve, validators write no miner winner weights.

After a solve, the current winner set receives 100% miner weight until the next
target is solved. A single winner gets all of it. If more than one miner verifies
in the same validator batch, those UIDs split the reward equally.

Duplicate submissions for an already-solved target do not change rewards.

Difficulty labels are only operator planning metadata. They do not change reward
weight.

## Verification

Miners submit only `proof_script`. The verifier builds the bridge target
`Solution`, so the submitted theorem must match the locked statement. `sorry`,
`admit`, new axioms, unsafe code, timeouts, and mismatched theorem statements do
not win.

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
mechanisms should not carry into the WTA launch.
