# Miner

The v1 miner is a tiny proof-serving Axon daemon.

It does not run an LLM, retry a prover, score prose, or optimize proof
efficiency. Miners can use any external workflow they want, then submit the
finished Lean file locally.

## Store A Proof

```bash
uv run lemma submit \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
```

`lemma submit` verifies by default. A valid proof prints `verified=true`,
`proof_sha256=...`, `store=...`, and `ready_to_serve=true`. Use `--no-verify`
only when deliberately storing an unconfirmed proof.

Proofs are stored under `LEMMA_MINER_SUBMISSIONS_PATH` or
`~/.lemma/submissions.json`.

## Serve Proofs

```bash
uv run lemma miner start
```

When a validator polls, the miner checks that the requested target id,
statement, imports, Lean toolchain, and Mathlib revision match its stored
submission. If they match, it returns only `proof_script`. If not, it returns no
proof.

## Operational Notes

- `AXON_PORT` controls the miner port.
- `AXON_EXTERNAL_IP` should be set explicitly for production miners.
- Miner droplets are optional now; they are proof-serving hosts, not automation
  machines.
- The validator result is not returned over Axon; chain weights are the visible
  reward signal.
