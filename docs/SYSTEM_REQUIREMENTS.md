# System requirements (miners vs validators)

Rough guidance for single-machine setups. Scale up if you run many validators or heavy local models.

## Miner

| Need | Why |
| ---- | --- |
| **CPU** | A few cores are enough; most work is calling your prover (cloud API or your own GPU elsewhere). |
| **RAM** | **4–8 GB** is fine for the Lemma process + modest concurrency (`MINER_MAX_CONCURRENT_FORWARDS`). |
| **Disk** | **A few GB** for Python env + logs; no Lean toolchain required on the miner unless you self-host a prover. |
| **Network** | Must accept inbound validator traffic on **`AXON_PORT`** (default **8091**) and reach your LLM / prover API. |
| **Docker** | **Not required** for consensus. The miner only **submits** Lean source text; validators verify it. Use Docker only if *you* want a local check identical to validators. |

## Validator

| Need | Why |
| ---- | --- |
| **CPU** | **2+ cores** helps; Docker + Python run together. |
| **RAM** | **8 GB minimum**, **16 GB+** comfortable if Docker Lean containers and a local judge LLM share the box. |
| **Disk** | **20 GB+** for Docker images, Layer caches, and logs ([Affine-style validator doc](https://github.com/AffineFoundation/affine-cortex/blob/main/docs/VALIDATOR.md) quotes similar ballpark for lightweight validators; Lemma adds Lean). |
| **Docker** | **Yes, for production verification** of miner proofs: untrusted Lean runs in the **`lemma/lean-sandbox`** image ([VALIDATOR.md](VALIDATOR.md)). Without Docker you’d only use host Lean for **your own** testing (`LEMMA_USE_DOCKER=0`). |
| **Judge stack** | Default design is **[Chutes](https://chutes.ai/)** OpenAI-compatible HTTP (`Qwen/Qwen3-32B-TEE`): reliable outbound network and API key. Self-hosted **vLLM** remains supported if you prefer a local GPU. Details: [MODELS.md](MODELS.md). |

## Epochs and answer deadlines vs hard problems

Each epoch samples **one** problem and miners get **`DENDRITE_TIMEOUT_S`** (default **3600 s** / 60 minutes in shipped config) to answer **that one** challenge—not the whole catalog in one sitting. **Round frequency** (how often scoring runs) follows **Bittensor subnet tempo**, not this timeout. Over many epochs, easy and hard theorems both appear; **some problems will rarely be solved** in time. That’s expected. Mitigations are subnet governance: tune timeouts, **curate or stratify** the catalog (`topic`, difficulty tags), and avoid weight games when nobody verifies—see **`EMPTY_EPOCH_WEIGHTS_POLICY`** in [.env.example](../.env.example).

## Related

- [VALIDATOR.md](VALIDATOR.md), [MINER.md](MINER.md), [PRODUCTION.md](PRODUCTION.md)
