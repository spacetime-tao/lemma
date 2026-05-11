# System Requirements

These are rough starting points. Scale up for more miners, more validators, or
faster Lean checks.

## Miner

| Resource | Notes |
| --- | --- |
| CPU | A few cores are usually enough when inference is remote. |
| RAM | 4-8 GB is typical. |
| Disk | Repo, logs, and optional Lean cache. |
| Network | Inbound `AXON_PORT`; outbound to prover API. |
| Docker | Optional unless the miner runs local Lean verify. |

A small VPS is often enough for a miner.

If `LEMMA_MINER_LOCAL_VERIFY=1`, size the host more like a light validator.

## Validator

| Resource | Notes |
| --- | --- |
| CPU | 2+ cores minimum. More helps with parallel verify. |
| RAM | 16 GB recommended. |
| Disk | 20 GB or more for Docker images and Lean caches. |
| Docker | Required for production validation. |
| Profile | Must match subnet policy. See [models.md](models.md). |

Cheap 4 GB instances are useful for miner tests, not production validators.

Use Linux with persistent SSD cache before judging 5- or 10-minute theorem
windows.

## Rounds And Timeouts

Validator rounds follow subnet epoch boundaries.

Each round samples one problem. Miners answer within the forward HTTP wait.
`LEAN_VERIFY_TIMEOUT_S` defaults to `300` seconds for each proof.

Governance may tune timeouts or `EMPTY_EPOCH_WEIGHTS_POLICY`.

## Related

- [validator.md](validator.md)
- [miner.md](miner.md)
- [production.md](production.md)
