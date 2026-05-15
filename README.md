# Lemma

**Lemma is a Bittensor subnet for turning formal mathematics targets
into machine-checked Lean proofs.**

The live reward path is deliberately narrow:

1. Validators publish one ordered known-theorem target at a time from a pinned manifest.
2. Miners locally verify a proof, keep it private, and publish an on-chain commitment.
3. After the commit window closes, miners reveal `proof_script` plus the secret nonce.
4. Validators verify the commitment, then verify the Lean file against the locked target.
5. Passing solvers are written to the solved-target ledger.
6. Accepted proof receipts make verified proofs replayable after acceptance.
7. The current verified solver set receives miner weight until the next target is solved.

No prose score, proof-efficiency score, difficulty multiplier, subjective judge,
or hidden validator discretion is part of the reward path.

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

Start from the repo:

```bash
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
uv run lemma setup
uv run lemma status
```

Mine the active target:

```bash
uv run lemma mine
# or choose one registered miner hotkey explicitly
uv run lemma mine --hotkey lemmaminer2
```

`lemma mine` shows the active theorem, asks whether to submit a proof, verifies
the pasted `Submission.lean`, publishes the private commitment, and starts the
miner server. If a proof is already committed, it resumes serving.

Run a validator:

```bash
uv run lemma setup --role validator
uv run lemma validate
# or run validation with a separate registered validator hotkey
uv run lemma validate --hotkey lemmaminer2
```

Advanced/script commands remain callable but are hidden from the main help:

```bash
uv run lemma submit \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
uv run lemma commit --problem known/smoke/nat_two_plus_two_eq_four
uv run lemma miner start
uv run lemma dashboard export --output data/miner-dashboard.json
uv run lemma portal start
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
- Validators choose the active target as `manifest - solved_ledger`, but a row
  only counts when its theorem statement hash matches the current manifest.
- The first target requires `LEMMA_TARGET_GENESIS_BLOCK`; each next target starts
  at the previous target's accepted block plus one.
- The default commit window is `LEMMA_COMMIT_WINDOW_BLOCKS=25`; validators poll
  for proofs only after reveal opens.
- Accepted proof receipts include proof text, nonce, commitment hash/timing,
  target fingerprint, validator hotkey, solver UID/hotkey, and proof hash for
  public replay.
- Targets with known accepted Lean proofs are not launch-eligible.
- Each target row carries a human proof reference, imports, attribution, and
  reviewer duplicate/faithfulness notes.
- Difficulty labels are operator planning metadata, not reward weights.
- The earliest valid commitment block wins. If multiple valid solvers committed
  in that same block, they split.
- If no target has been solved yet, validators do not write miner weights.
- Duplicate proofs for already-solved targets do not change the active solver set.
- The public miner dashboard is a static export from the manifest, solved
  ledger, and accepted-proof receipts.
- An optional portal candidate lane can host wallet-submitted miner proofs, but
  validators still require the same commitment and Lean verification.
- Launch on a fresh or intentionally reset subnet state so old Lemma weights do
  not carry into the proof protocol.

See [`docs/protocol.md`](docs/protocol.md) for the compact mechanism reference.

## License

Apache-2.0.

## Original Contributors

Spaceτime, Maciej Kula, and Infinitao.
