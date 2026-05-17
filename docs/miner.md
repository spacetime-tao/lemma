# Miner

A Lemma miner receives theorem challenges, asks a prover model for a Lean
`Submission.lean`, and returns the proof for validators to check.

This page is the complete miner path: install, keys, `.env`, registration,
readiness checks, and the live axon.

## Miner command map

| Goal | Command |
| --- | --- |
| Configure env, wallet, prover, and axon port | `uv run lemma setup --role miner` |
| See current chain/theorem state | `uv run lemma status` |
| Check miner readiness | `uv run lemma miner check` |
| Print config without binding a port | `uv run lemma miner dry-run` |
| Start the axon | `uv run lemma miner start` |
| Explain logs and score visibility | `uv run lemma miner observability` |
| Try one theorem locally | `uv run lemma proof preview` |

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

Create a coldkey and a miner hotkey:

```bash
uv run btcli wallet new_coldkey --wallet.name my_wallet --n_words 12
uv run btcli wallet new_hotkey --wallet.name my_wallet --wallet.hotkey miner
uv run btcli wallet list
```

Keep the coldkey local or offline. A server only needs the miner hotkey.

## Configure

```bash
uv run lemma setup --role miner
```

The setup flow writes `.env`. For a miner, the important values are:

```text
SUBTENSOR_NETWORK=test
NETUID=467
BT_WALLET_COLD=my_wallet
BT_WALLET_HOT=miner
AXON_EXTERNAL_IP=<public-ip-or-hostname>
AXON_PORT=8091
PROVER_PROVIDER=openai
PROVER_OPENAI_BASE_URL=<openai-compatible-base-url>
PROVER_OPENAI_API_KEY=<provider-key>
PROVER_MODEL=<model-name>
```

For the current public test deployment, use Bittensor testnet subnet 467 unless
a different deployment is explicitly published.

## Register

Use the same network and netuid from `.env`:

```bash
uv run btcli subnet show --netuid 467 --network test
uv run btcli subnet register --netuid 467 --network test --wallet.name my_wallet --wallet.hotkey miner
```

Open inbound `AXON_PORT` so validators can reach the miner. On a VPS, set
`AXON_EXTERNAL_IP` to the public IPv4 or DNS name.

## Check

```bash
uv run lemma status
uv run lemma miner check
uv run lemma miner dry-run
```

`lemma miner check` should report the wallet, chain RPC, and registered subnet
UID as ready before you leave the miner running.

## Prover model

Miners need a prover model that can write valid Lean. The setup flow asks which
provider to use and then asks for the model and key values.

Supported paths are provider-neutral:

- Chutes, the documented default OpenAI-compatible host.
- Hosted OpenAI through the same OpenAI-compatible shape.
- Gemini through Google's OpenAI-compatible endpoint.
- Anthropic, installed with `uv sync --extra anthropic`.
- A custom OpenAI-compatible base URL such as vLLM, LiteLLM, or another gateway.

Details and example environment variables are in [models.md](models.md).

## Run

```bash
uv run lemma status
uv run lemma miner check
uv run lemma miner start
```

The miner starts solving as soon as a validator forwards a challenge. It does
not wait for a new block window after the request arrives.

Useful options:

```bash
uv run lemma miner start --max-forwards-per-day 100
uv run lemma miner start --hotkey my_second_hotkey --port 8092
```

Each hotkey is a separate miner identity. If multiple hotkeys run on one
machine, give each one its own axon port and open only the ports you actually
use.

## What the miner can see

Validators decide whether the submitted proof passes Lean. The miner axon does
not receive final validator scores back over the request path.

Useful local signals:

- `miner answered` means the miner produced a reply.
- `LEMMA_MINER_LOCAL_VERIFY=1` runs the same local Lean verification path after
  the prover returns, if Docker and the sandbox image are available.
- `LEMMA_MINER_FORWARD_TIMELINE=1` adds receive, solved, and outcome timeline
  logs for each forward.
- `uv run lemma proof preview` runs one prover attempt against the current
  theorem and verifies by default.

Final miner ranking still comes from validator-published weights and the chain
metagraph, not from a local miner log line.

## Proof contract

The returned `proof_script` must be a complete Lean file in the `Submission`
namespace, proving the exact theorem name and statement the validator sent.

Cadence submissions are allowlisted: exact imports, `namespace Submission`, one
exact target theorem, the proof body, and `end Submission`. Extra imports,
helper declarations, custom syntax/macros/elaborators, notation, attributes,
unsafe/native/debug hooks, new assumptions, changed theorem statements, and
incomplete files are rejected.
