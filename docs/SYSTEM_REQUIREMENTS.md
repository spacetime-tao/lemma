# System requirements

Single-machine guidance; scale up for many validators or large local models.

## Miner

| Resource | Notes |
| -------- | ----- |
| CPU | Few cores; work is mostly remote inference or GPU elsewhere. |
| RAM | 4–8 GB typical. |
| Disk | Few GB for Python env and logs; Lean toolchain only if proving locally. |
| Network | Inbound **`AXON_PORT`** (default **8091**); outbound to prover API. |
| Docker | Not required for consensus. |

## Validator

| Resource | Notes |
| -------- | ----- |
| CPU | 2+ cores. |
| RAM | ≥ 8 GB; 16 GB if Docker + local judge LLM. |
| Disk | ≥ 20 GB for images and caches. |
| Docker | Required for production verification (`lemma/lean-sandbox` image). Host-only Lean possible with **`LEMMA_USE_DOCKER=0`** for debugging. |
| Judge | Default Chutes OpenAI-compatible endpoint; alternative vLLM ([MODELS.md](MODELS.md)). |

## Epochs and timeouts

Each epoch samples **one** problem; miners answer within **`DENDRITE_TIMEOUT_S`** (default **3600** s). Subnet **tempo** controls how often epochs occur. Hard problems may often timeout — governance may tune timeouts or catalogs (**`EMPTY_EPOCH_WEIGHTS_POLICY`** in [`.env.example`](../.env.example)).

## Related

[VALIDATOR.md](VALIDATOR.md), [MINER.md](MINER.md), [PRODUCTION.md](PRODUCTION.md)
