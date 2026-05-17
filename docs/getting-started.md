# Getting started

This guide gets one checkout ready for Lemma commands, Bittensor keys, bounty
claiming, and validator-side checking.

Lemma currently runs on Bittensor testnet as subnet 467. Use `--network test`
and `--netuid 467` unless a different deployment is explicitly published.

## Command map

| Goal | Command |
| --- | --- |
| First-time setup | `uv run lemma setup` |
| Browse or claim bounties | `uv run lemma mine` |
| Bounty market status | `uv run lemma status` |
| Validator escrow preflight | `uv run lemma validate --check` |

Run `uv run lemma --help` for the public CLI surface. Lower-level cadence
operator commands remain available but are not the normal bounty path.

## Install and sync

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
```

Use one environment and one installer: `uv`. The `btcli` command comes from the
official Bittensor packages installed through the `btcli` extra. Do not install
a separate package named `btcli`.

## Keys

Create a coldkey and at least one hotkey. The hotkey is what a miner or
validator service uses on a machine.

```bash
uv run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
uv run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
uv run btcli wallet balance --wallet.name my_wallet
```

Keep coldkeys local or offline. For VPS details, read
[vps-safety.md](vps-safety.md).

## Configure Lemma

```bash
uv run lemma setup
```

The setup flow writes `.env`. It asks for chain settings, wallet names, prover
settings for miners, axon port, and validator Lean settings when relevant.

Provider setup is OpenAI-compatible by default. Chutes is the documented
default host, and custom OpenAI-compatible bases are supported. Gemini's
OpenAI-compatible endpoint, Anthropic, hosted OpenAI, and local gateways are
covered in [models.md](models.md).

For validator machines, run:

```bash
uv run lemma setup --role validator
```

## Register on testnet

Use the same network and netuid that `lemma setup` wrote into `.env`.

```bash
uv run btcli subnet show --netuid 467 --network test
uv run btcli subnet register --netuid 467 --network test --wallet.name my_wallet --wallet.hotkey miner
```

Validators also need stake on the validator hotkey before they can publish
weights.

## Miner path

```bash
uv run lemma status
uv run lemma mine
```

`lemma mine` lists escrow-backed live bounties first. Draft targets are useful
for local proof work, but they are not reward offers until a funded escrow row
exists on-chain.

Full miner notes: [miner.md](miner.md).

## Validator path

Build the Lean sandbox image first, then check escrow configuration:

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validate --check
```

Validators never handle bounty custody keys. They fetch revealed artifacts, run
Lean, and submit escrow attestations under the configured policy. Full validator
notes: [validator.md](validator.md).

## Bounties

Bounties are live only when funded in `LemmaBountyEscrow` on Bittensor EVM.
There is no live manual payout path.

```bash
uv run lemma mine
uv run lemma mine <bounty-id> --submission Submission.lean
uv run lemma mine <bounty-id> --submission Submission.lean --commit --claimant-evm 0x... --payout-evm 0x...
uv run lemma mine <bounty-id> --submission Submission.lean --reveal --claimant-evm 0x... --payout-evm 0x... --salt 0x...
```

Details: [bounties.md](bounties.md).
