# System requirements

Rough guidance for one machine; scale for heavy workloads.

## Miner

| Resource | Notes |
| -------- | ----- |
| CPU | Few cores; inference often remote. |
| RAM | 4–8 GB typical. |
| Disk | Small checkout + logs; a full local **Lean** toolchain + Mathlib cache only if you prove or verify on-host (e.g. `lemma proof preview --host-lean`, dev workflows). |
| Network | Inbound `AXON_PORT` (default 8091); outbound to prover API. |
| Docker | Optional for miners unless you run local verify mirroring validators. |

A small VPS is often enough for a remote miner when inference is handled by an
API provider. If `LEMMA_MINER_LOCAL_VERIFY=1` is enabled, size it more like a
light validator because Docker + Mathlib caches become part of the hot path.

## Validator

| Resource | Notes |
| -------- | ----- |
| CPU | 2+ cores. |
| RAM | **≥ 16 GB** recommended: Docker sandbox + Lake/Mathlib workspace caches, plus OS headroom. Validators verify Lean locally or through a remote Lean worker; they do not need local inference weights for proof scoring. |
| Disk | ≥ 20 GB for images and caches. |
| Docker | **Required** for production: host Docker daemon plus lean-sandbox image. The Lemma runtime image uses the host socket through the Python Docker SDK and does not bundle a Docker daemon. `LEMMA_USE_DOCKER=false` is for **local debugging only**, not a supported production mode. |
| Profile | Pinned verifier/scoring profile per subnet policy — see [models.md](models.md). |

Cheap 4 GB VPS instances are useful for miner tests, but they are not a good
validator target once Lean verification is in the loop. Use production-like
Linux hardware with persistent SSD cache before drawing conclusions about 5- or
10-minute theorem windows.

## Rounds and timeouts

Validator rounds follow the published problem-seed windows. With the default 100-block quantized window, expect about 72 theorem windows per day.

Each round samples one problem; miners answer within the subnet’s **forward HTTP wait** (blocks × block time, clamped — see [technical-reference.md](technical-reference.md)). `LEAN_VERIFY_TIMEOUT_S` defaults to 300 s for sandbox — raise if Mathlib builds legitimately exceed that. Governance may tune timeouts and rolling scoring settings (`.env.example`).

## Related

[validator.md](validator.md), [miner.md](miner.md), [production.md](production.md)
