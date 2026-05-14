# Lemma

**Lemma is Bittensor Testnet Subnet 467 for turning formal mathematics targets
into machine-checked Lean proofs.**

The live reward path is deliberately narrow:

1. Validators publish one ordered known-theorem target at a time from a pinned manifest.
2. Miners submit one reward-critical artifact: `proof_script`.
3. Validators verify the submitted Lean file against the locked target.
4. Passing solvers are written to the solved-target ledger.
5. The current verified solver set receives miner weight until the next target is solved.

No prose score, proof-efficiency score, difficulty multiplier, subjective judge,
or commit-reveal ceremony is part of the reward path.

## Current Scope

The public package, command, and docs are `lemma`. The internal Python package is
also `lemma`.

The default problem source is:

```bash
LEMMA_PROBLEM_SOURCE=known_theorems
```

The active target supply is vendored in
[`lemma/problems/known_theorems_manifest.json`](lemma/problems/known_theorems_manifest.json).
The current queue is Mathlib-only smoke-test material for proving the protocol
and CLI flow before launch-quality targets are curated.

## Quick Start

From this checkout:

```bash
uv sync --extra btcli
uv run lemma --help
uv run lemma target show
uv run lemma target ledger
uv run lemma meta
```

Verify a candidate proof file against a locked target:

```bash
uv run lemma verify \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
```

Store a verified proof for the miner daemon, then run a miner or validator:

```bash
uv run lemma submit \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
uv run lemma miner start
uv run lemma validator check
uv run lemma validator start
```

Validators must pin both the validator profile hash and the known-theorem
manifest hash before live use:

```bash
uv run lemma meta --raw
```

## Protocol Notes

- The operator-published ledger is the source of truth for solved targets.
- Validators choose the active target as `manifest - solved_ledger`.
- Targets with known accepted Lean proofs are not launch-eligible.
- Each target row carries a human proof reference, imports, attribution, and
  reviewer duplicate/faithfulness notes.
- Difficulty labels are operator planning metadata, not reward weights.
- If multiple miners verify in the same batch, those UIDs split the reward equally.
- If no target has been solved yet, validators do not write miner weights.
- Duplicate proofs for already-solved targets do not change the active solver set.
- Launch on a fresh or intentionally reset subnet state so old Lemma weights do
  not carry into the proof protocol.

See [`docs/protocol.md`](docs/protocol.md) for the compact mechanism reference.

## License

Apache-2.0.

## Original Contributors

Spaceτime, Maciej Kula, and Infinitao.
