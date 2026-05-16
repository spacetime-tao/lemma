# Getting started

This guide gets one checkout ready for Lemma commands, Bittensor keys, miner
operation, validator operation, and bounties.

Lemma currently runs on Bittensor testnet as subnet 467. Use `--network test`
and `--netuid 467` unless a different deployment is explicitly published.

## Command map

| Goal | Command |
| --- | --- |
| First-time setup | `uv run lemma setup` |
| Current chain/theorem view | `uv run lemma status` |
| Miner preflight | `uv run lemma miner check` |
| Start miner | `uv run lemma miner start` |
| Validator preflight | `uv run lemma validator check` |
| Validator rehearsal | `uv run lemma validator dry-run` |
| Start validator | `uv run lemma validator start` |
| Prover smoke test | `uv run lemma proof preview` |
| Bounty list/show/verify | `uv run lemma bounty ...` |

Run `uv run lemma --help` for the full CLI surface.

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
uv run lemma miner check
uv run lemma miner start
```

Open inbound `AXON_PORT` so validators can reach the miner. Set
`AXON_EXTERNAL_IP` on production hosts, or opt into public-IP discovery with
`AXON_DISCOVER_EXTERNAL_IP=true`.

Full miner notes: [miner.md](miner.md).

## Validator path

Build the Lean sandbox image first:

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator check
uv run lemma validator dry-run
uv run lemma validator start
```

Use `dry-run` before live validation when changing host, wallet, verifier, or
profile settings. Full validator notes: [validator.md](validator.md).

## Bounties

Bounties are submit-when-ready proof targets and do not require miner
registration.

```bash
uv run lemma bounty list
uv run lemma bounty show smoke.two_plus_two
uv run lemma bounty verify smoke.two_plus_two --submission Submission.lean
uv run lemma bounty package smoke.two_plus_two --submission Submission.lean --payout <SS58>
uv run lemma bounty submit smoke.two_plus_two --submission Submission.lean --payout <SS58>
```

Details: [bounties.md](bounties.md).
