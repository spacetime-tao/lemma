# Miner

A Lemma miner receives theorem challenges, asks a prover model for a Lean
`Submission.lean`, and returns the proof for validators to check.

Start with [getting-started.md](getting-started.md) if the repo, keys, and
`.env` are not configured yet.

## Miner command map

| Goal | Command |
| --- | --- |
| Configure env, wallet, prover, and axon port | `uv run lemma setup` |
| See current chain/theorem state | `uv run lemma status` |
| Check miner readiness | `uv run lemma miner check` |
| Print config without binding a port | `uv run lemma miner dry-run` |
| Start the axon | `uv run lemma miner start` |
| Explain logs and score visibility | `uv run lemma miner observability` |
| Try one theorem locally | `uv run lemma proof preview` |

## Setup checklist

1. `uv sync --extra btcli`
2. Create a coldkey and miner hotkey with `uv run btcli`.
3. Run `uv run lemma setup`.
4. Register the miner hotkey on the same network/netuid as `.env`.
5. Open `AXON_PORT`.
6. Run `uv run lemma miner check`.
7. Run `uv run lemma miner start`.

For the current public test deployment, use Bittensor testnet subnet 467.

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
