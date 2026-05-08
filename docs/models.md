# Inference models

Lemma uses OpenAI-compatible HTTP (`/v1/chat/completions`). [Chutes](https://chutes.ai/) is the default documented host.

## Catalog

```bash
curl -sS https://llm.chutes.ai/v1/models | jq '.data[] | {id, pricing}'
```

Use `id` as `OPENAI_MODEL`.

## Validators (judge)

**Required** for `lemma validator`: `JUDGE_PROVIDER=chutes`, `OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2-TEE`, and `OPENAI_BASE_URL=https://llm.chutes.ai/v1` — no self-hosted or alternate judge stack for scoring (`openai` remains a legacy alias for the same HTTP client path). Set **`JUDGE_OPENAI_API_KEY`** to your Chutes inference token (or legacy **`OPENAI_API_KEY`** if you keep a single judge key there). Miners use `PROVER_*` and may call any prover model the operator runs.

One pinned stack per subnet: `uv run lemma meta` → `judge_profile_sha256` → optional `JUDGE_PROFILE_SHA256_EXPECTED`.

Judge emits short JSON. After changing endpoints or models, rerun `uv run lemma meta` and redistribute hashes.

## Miners (prover)

Use a **reasoning-capable** model that writes valid `Submission.lean`. Recommended baseline on Chutes: the same family as the subnet judge (`deepseek-ai/DeepSeek-V3.2-TEE`) or another strong reasoning model you operate reliably.

| Goal | Examples |
| ---- | -------- |
| Align with subnet judge tier | `deepseek-ai/DeepSeek-V3.2-TEE` |
| Other reasoning options | Other DeepSeek / Qwen / frontier reasoning listings on Chutes |

Set `PROVER_PROVIDER=openai`, **`PROVER_OPENAI_BASE_URL`** (or rely on judge `OPENAI_BASE_URL` if unset), **`PROVER_OPENAI_API_KEY`** (or legacy `OPENAI_API_KEY` fallback), and **`PROVER_MODEL`** (miner-only id; falls back to `OPENAI_MODEL` if unset). Optional `model_card` for training exports.

The live miner (`lemma miner`) starts solving **as soon as** a validator forwards a challenge — no deliberate wait for block ticks. `lemma try-prover` is separate (manual smoke test).

Custom **`PROVER_OPENAI_BASE_URL`** / keys for the **prover** are normal (any OpenAI-compatible host you operate). The **subnet judge** for validators stays on the pinned Chutes stack above—self-hosted judge endpoints are not the default production path.
