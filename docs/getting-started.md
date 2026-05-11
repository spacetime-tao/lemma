# Getting Started

This is the shortest path from a fresh repo to a miner or validator.

Definitions:

- A miner looks for Lean proofs.
- A validator checks proofs and writes weights.
- A hotkey is the key a running service uses.
- A coldkey should stay local and safe.
- An epoch is one subnet round.

Lemma currently runs on Bittensor testnet:

- Network: `test`
- Subnet: `467`
- Mainnet: Finney

## Install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli --extra cli
```

Use `uv run lemma` for core commands. Use `uv run lemma-cli` for friendlier
operator commands.

## Package Names

Use the official Bittensor packages.

```bash
uv sync --extra btcli --extra cli
```

This installs the `btcli` command from the official `bittensor-cli` package.
Do not install a package named `btcli`.

## Keys

Create or import keys with `btcli`.

```bash
uv run btcli wallet new_coldkey --wallet.name lemma
uv run btcli wallet new_hotkey --wallet.name lemma --wallet.hotkey miner
```

Keep the coldkey off servers when possible. Put only the hotkey on a VPS.

More key safety notes: [vps-safety.md](vps-safety.md).

## Configure

Run the setup wizard:

```bash
uv run lemma-cli setup
```

The wizard writes `.env`. It sets testnet and `NETUID=467`. It also asks for
wallet names, prover keys, axon port, and validator Lean image settings.

## Register

Use the same network and subnet as `.env`.

```bash
uv run btcli subnet register --netuid 467 --network test
```

Follow the `btcli` prompts. Make sure your wallet has enough testnet funds.

## Miner Path

```bash
uv run lemma miner dry-run
uv run lemma-cli rehearsal
uv run lemma miner start
```

Before `miner start`, open inbound `AXON_PORT`. For production miners, set
`AXON_EXTERNAL_IP`. You can also set `AXON_DISCOVER_EXTERNAL_IP=true`.

More detail: [miner.md](miner.md).

## Validator Path

Build the Lean image before starting a validator:

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma-cli rehearsal
uv run lemma validator-check
uv run lemma validator start
```

Use `uv run lemma validator start` from the repo root. Do not start validators
through ad-hoc Python entrypoints.

More detail: [validator.md](validator.md).

## Common Checks

| Need | Command |
| --- | --- |
| Core help | `uv run lemma --help` |
| Friendly CLI help | `uv run lemma-cli --help` |
| Miner smoke test | `uv run lemma miner dry-run` |
| Prover plus Lean preview | `uv run lemma-cli rehearsal` |
| Validator readiness | `uv run lemma validator-check` |
| Start miner | `uv run lemma miner start` |
| Start validator | `uv run lemma validator start` |

## Next Docs

- [miner.md](miner.md)
- [validator.md](validator.md)
- [models.md](models.md)
- [testing.md](testing.md)
