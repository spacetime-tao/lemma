# Getting Started

## Install

```bash
uv sync --extra btcli
uv run lemma --help
```

## Inspect Targets

```bash
uv run lemma target show
uv run lemma target ledger
uv run lemma meta
```

The active target is the first known-theorem manifest row that is not present in
the solved ledger.

## Submit A Proof

Create a complete `Submission.lean`, then verify and store it for the miner
daemon:

```bash
uv run lemma submit \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
```

`submit` verifies by default and prints `verified=true` plus
`ready_to_serve=true` only after Lean accepts the proof. Host Lean is local-only
and requires `LEMMA_ALLOW_HOST_LEAN=1` plus `--host-lean`.

## Run A Miner

```bash
uv run lemma miner start
```

The miner serves a stored proof only when the validator polls the exact matching
target. Miner droplets are optional proof-serving hosts; proof search itself can
happen offline on a laptop or workstation.

## Run A Validator

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma meta --raw
uv run lemma validator check
uv run lemma validator dry-run
uv run lemma validator start
```

The validator service should stay live for subnet operation: it polls miners,
verifies proofs with Lean, appends the solved ledger, and sets winner weights.

More detail: [wta.md](wta.md), [miner.md](miner.md), [validator.md](validator.md),
and `.env.example`.
