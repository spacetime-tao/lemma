# Getting Started

## Install

```bash
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
```

## Setup

```bash
uv run lemma setup
uv run lemma status
```

The active target is the first known-theorem manifest row that is not present in
the solved ledger, followed by deterministic generated cadence tasks. A fresh
validator needs `LEMMA_TARGET_GENESIS_BLOCK` so every miner sees the same first
commit window.

Optional proof search tools use OpenAI-compatible provider settings:

```bash
LEMMA_PROVER_BASE_URL=https://your-provider.example/v1
LEMMA_PROVER_API_KEY=replace_me
LEMMA_PROVER_MODEL=your-model
```

## Mine

The friendly path shows the active theorem, asks whether you are ready, verifies
the pasted `Submission.lean`, publishes the commitment, and starts the miner:

```bash
uv run lemma mine
```

Pick a specific registered miner hotkey with:

```bash
uv run lemma mine --hotkey lemmaminer2
```

If the chain commitment failed after local verification, retry it without
resubmitting the proof:

```bash
uv run lemma mine --retry-commit
```

Advanced scripts can still call the hidden building blocks:

```bash
uv run lemma submit \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
uv run lemma commit --problem known/smoke/nat_two_plus_two_eq_four
uv run lemma miner start
```

The miner serves a stored proof only when the validator polls the exact matching
target during reveal phase. During commit phase it serves no proof text. Miner
droplets are optional proof-serving hosts; proof search itself can happen
offline on a laptop or workstation.

Keep the miner running until your UID appears on
`https://lemmasub.net/cadence/`. `lemma target ledger` is useful only when you
have the validator/operator ledger locally. Validators poll on their own
schedule, then run Lean verification; the default poll interval is about five
minutes after reveal opens.

## Verify A Bounty

Formal Conjectures bounties are manual winner-take-all campaigns and do not
require a subnet UID:

```bash
uv run lemma mine --bounty <campaign-id> --submission Submission.lean
```

## Run A Validator

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma setup --role validator
uv run lemma validate
```

If the validator should use a different registered hotkey than the miner, pass
it directly:

```bash
uv run lemma setup --role validator --hotkey lemmaminer2
uv run lemma validate --hotkey lemmaminer2
```

The validator service should stay live for subnet operation: it polls miners,
verifies proofs with Lean, appends the solved ledger, and sets miner weights.
The public cadence export shows task state and full solver hotkeys. Proof text,
proof hashes, nonces, and commitments stay out of the public site feed.

More detail: [protocol.md](protocol.md), [miner.md](miner.md),
[validator.md](validator.md), and `.env.example`.
