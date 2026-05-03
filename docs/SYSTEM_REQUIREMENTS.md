# System requirements

Rough guidance for one machine; scale for heavy workloads.

## Miner

| Resource | Notes |
| -------- | ----- |
| CPU | Few cores; inference often remote. |
| RAM | 4–8 GB typical. |
| Disk | Small env + logs; Lean toolchain only if proving locally. |
| Network | Inbound `AXON_PORT` (default 8091); outbound to prover API. |
| Docker | Not required for consensus. |

## Validator

| Resource | Notes |
| -------- | ----- |
| CPU | 2+ cores. |
| RAM | ≥ 8 GB; 16 GB if Docker + local judge LLM. |
| Disk | ≥ 20 GB for images and caches. |
| Docker | Production verification uses the lean-sandbox image. `LEMMA_USE_DOCKER=0` for host-only debugging. |
| Judge | Default Chutes; vLLM alternative ([MODELS.md](MODELS.md)). |

## Rounds and timeouts

Timer-based rounds by default (`LEMMA_VALIDATOR_ROUND_INTERVAL_S`, 300 s). `LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH=1` ties rounds to chain epochs.

Each round samples one problem; miners answer within the subnet’s **forward HTTP wait** (blocks × block time, clamped — see [FAQ.md](FAQ.md)). `LEAN_VERIFY_TIMEOUT_S` defaults to 300 s for sandbox — raise if Mathlib builds legitimately exceed that. Governance may tune timeouts or `EMPTY_EPOCH_WEIGHTS_POLICY` (`.env.example`).

## Related

[VALIDATOR.md](VALIDATOR.md), [MINER.md](MINER.md), [PRODUCTION.md](PRODUCTION.md)
