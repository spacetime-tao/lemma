# Miner

A miner tries to solve a theorem by returning a Lean proof script.

The included miner is a reference implementation. It is useful for testing and
for running the subnet end to end. It is not the final answer to every mining or
training question.

## Quick Path

```bash
uv run lemma-cli setup
uv run btcli subnet register --netuid 467 --network test
uv run lemma miner dry-run
uv run lemma-cli rehearsal
uv run lemma miner start
```

Before `miner start`, open inbound `AXON_PORT`. Set `AXON_EXTERNAL_IP` for a
production miner.

## What Happens During Mining

1. A validator sends your miner a theorem.
2. Your miner calls the configured prover API.
3. The prover returns `proof_script`.
4. The miner sends the proof back to the validator.
5. The validator checks it with Lean.

Only the validator's Lean check decides whether the proof can enter scoring.

## Prover Settings

Miner model settings use `PROVER_*` variables. See [models.md](models.md).

The miner uses the fixed `PROVER_SYSTEM` prompt in
[`lemma/miner/prover.py`](../lemma/miner/prover.py). There is no extra prompt
append from `.env`.

## Local Verify

Set this to make the miner run Lean locally before answering:

```bash
LEMMA_MINER_LOCAL_VERIFY=1
```

Local verify costs time, but it can catch bad proofs before the validator sees
them. The validator still runs its own check unless a future policy says
otherwise.

## Logs

Useful log fields:

- `my_uid`: your UID from the chain metagraph.
- `my_incentive`: current chain incentive for your hotkey.
- `miner answered`: the miner sent a response.

For a short timeline per request:

```bash
LEMMA_MINER_FORWARD_TIMELINE=1
```

This prints receive, solve, and outcome lines for each validator forward.

## What Does Not Happen

- The miner does not receive final validator weights on the axon response.
- `lemma-cli try-prover` is not live mining.
- Repeating a local success does not create rewards by itself.

## Related Docs

- [getting-started.md](getting-started.md)
- [models.md](models.md)
- [faq.md](faq.md)
- [miner-verify-attest.md](miner-verify-attest.md)
