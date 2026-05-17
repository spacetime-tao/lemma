# Validator

A Lemma validator verifies Lean proofs. In the bounty path, validators never
hold reward funds; they attest to revealed escrow claims after local
verification. In the cadence path, validators send theorem challenges to miners
and publish weights for eligible work.

This page is the complete validator path: install, keys, `.env`, registration,
stake, Lean verification, dry run, and live validation.

## Validator command map

| Goal | Command |
| --- | --- |
| Configure validator env | `uv run lemma setup --role validator` |
| Check bounty escrow config | `uv run lemma validate --check` |
| Check chain, wallet, profile, and Lean readiness | `uv run lemma validator check` |
| Print validator config | `uv run lemma validator config` |
| Rehearse full epochs without `set_weights` | `uv run lemma validator dry-run` |
| Start live validation | `uv run lemma validator start` |
| Run a remote Lean worker | `uv run lemma validator lean-worker` |
| Serve profile hash for peers | `uv run lemma validator profile-attest-serve` |
| Inspect profile hash | `uv run lemma config meta` |

## Install

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
```

Use one installer and one environment: `uv`. The `btcli` command comes from the
Bittensor packages installed by the `btcli` extra.

## Keys

Create a coldkey and a validator hotkey:

```bash
uv run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
uv run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey validator
uv run btcli wallet list
```

Keep the coldkey local or offline. A server only needs the validator hotkey.

## Configure

```bash
uv run lemma setup --role validator
```

The setup flow writes `.env`. For a validator, the important values are:

```text
SUBTENSOR_NETWORK=test
NETUID=467
BT_WALLET_COLD=my_wallet
BT_WALLET_HOT=validator
BT_VALIDATOR_WALLET_COLD=my_wallet
BT_VALIDATOR_WALLET_HOT=validator
LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest
LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=.lemma-lean-cache
```

For the current public test deployment, use Bittensor testnet subnet 467 unless
a different deployment is explicitly published.

## Register and stake

Use the same network and netuid from `.env`:

```bash
uv run btcli subnet show --netuid 467 --network test
uv run btcli subnet register --netuid 467 --network test --wallet.name my_wallet --wallet.hotkey validator
uv run btcli stake add --wallet-name my_wallet --hotkey validator --network test --netuid 467
```

Register and stake from the coldkey machine. Copy only the validator hotkey to a
VPS.

## Lean verification

Validators need Docker or a compatible Lean verification setup. The production
default is Docker with the pinned Lean sandbox image.

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator check
uv run lemma validator dry-run
```

For faster steady-state verification, run a long-lived Docker worker and point
Lemma at it with `LEMMA_LEAN_DOCKER_WORKER`. Put the workspace cache on fast
local disk with `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`.

Important verifier docs:

- [toolchain-image-policy.md](toolchain-image-policy.md)
- [validator_lean_load.md](validator_lean_load.md)
- [production.md](production.md)

## Live validation

For escrow-backed bounties:

```bash
uv run lemma validate --check
uv run lemma validate --once
```

The validator path is custody-free. It fetches revealed artifacts, verifies the
artifact hash and Lean proof under the pinned policy, then submits an on-chain
attestation. The current CLI checks escrow configuration; the remaining live
watcher work is the reveal-artifact transport recorded in [workplan.md](workplan.md).
The contract releases payout only after the threshold and challenge-window rules
are met.

```bash
uv run lemma validator start
```

Use `dry-run` before live validation when changing host, wallet, verifier,
profile, scoring, or problem-source settings. A passing dry run does not publish
weights; it is the rehearsal path.

Validator rounds follow the published problem-seed windows. Miners submit Lean
proof files, validators verify with the pinned policy, and only Lean-valid work
can become reward-eligible.

## Remote Lean worker

Use a remote worker when the validator host should handle networking and chain
work while another machine handles Lean.

On the worker:

```bash
uv run lemma validator lean-worker --host 0.0.0.0 --port 8787
```

Set `LEMMA_LEAN_VERIFY_REMOTE_BEARER` before binding to non-loopback hosts. On
the validator, set `LEMMA_LEAN_VERIFY_REMOTE_URL` and the same bearer token.

Keep worker ports private or tightly allowlisted. An unauthenticated public Lean
worker is not a safe production setup.

## Profile agreement

Validators should agree on verification and scoring policy. Inspect the local
profile hash with:

```bash
uv run lemma config meta
```

Optional peer attestation uses:

- `LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED=1`
- `LEMMA_VALIDATOR_PROFILE_ATTEST_PEER_URLS`
- `uv run lemma validator profile-attest-serve --host 0.0.0.0 --port 8799`

This is operator coordination, not a replacement for secure deployment
practices.
