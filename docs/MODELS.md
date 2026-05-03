# Inference models

Lemma uses OpenAI-compatible HTTP (`/v1/chat/completions`). [Chutes](https://chutes.ai/) is the default documented host.

## Catalog

```bash
curl -sS https://llm.chutes.ai/v1/models | jq '.data[] | {id, pricing}'
```

Use `id` as `OPENAI_MODEL`.

## Validators (judge)

**Required** on the default OpenAI-compatible path: `OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2-TEE` at `https://llm.chutes.ai/v1` (or the same HF-style id on your self-hosted vLLM). `lemma validator` refuses other ids unless `LEMMA_ALLOW_NONCANONICAL_JUDGE_MODEL=1` (experiments only).

One pinned stack per subnet: `uv run lemma meta` → `judge_profile_sha256` → optional `JUDGE_PROFILE_SHA256_EXPECTED`.

Judge emits short JSON. After changing endpoints or models, rerun `uv run lemma meta` and redistribute hashes.

## Miners (prover)

Use a **reasoning-capable** model that writes valid `Submission.lean`. Recommended baseline on Chutes: the same family as the subnet judge (`deepseek-ai/DeepSeek-V3.2-TEE`) or another strong reasoning model you operate reliably.

| Goal | Examples |
| ---- | -------- |
| Align with subnet judge tier | `deepseek-ai/DeepSeek-V3.2-TEE` |
| Other reasoning options | Other DeepSeek / Qwen / frontier reasoning listings on Chutes |

Set `PROVER_PROVIDER=openai`, `OPENAI_BASE_URL`, `OPENAI_API_KEY`, and `PROVER_MODEL` (miner-only id; falls back to `OPENAI_MODEL` if unset). Optional `model_card` for training exports.

The live miner (`lemma miner`) starts solving **as soon as** a validator forwards a challenge — no deliberate wait for block ticks. `lemma try-prover` is separate (manual smoke test).

## vLLM

`OPENAI_BASE_URL=http://127.0.0.1:8000/v1` (or `host.docker.internal` from containers). Realign `uv run lemma meta` with the subnet.
