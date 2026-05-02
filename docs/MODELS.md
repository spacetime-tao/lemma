# Inference models

Lemma uses OpenAI-compatible HTTP (`/v1/chat/completions`). [Chutes](https://chutes.ai/) is the default documented host.

## Catalog

```bash
curl -sS https://llm.chutes.ai/v1/models | jq '.data[] | {id, pricing}'
```

Use `id` as `OPENAI_MODEL`.

## Validators (judge)

One pinned stack per subnet: `uv run lemma meta` → `judge_profile_sha256` → optional `JUDGE_PROFILE_SHA256_EXPECTED`.

Default starting point: `Qwen/Qwen3-32B-TEE` at `https://llm.chutes.ai/v1`. Judge emits short JSON.

After changing endpoints or models, rerun `uv run lemma meta` and redistribute hashes.

## Miners (prover)

Any model that yields valid `Submission.lean`. Example goals on Chutes (verify pricing live):

| Goal | Examples |
| ---- | -------- |
| Low cost | Small instruct models |
| Code-oriented | `Qwen/Qwen2.5-Coder-32B-Instruct` |
| Stronger reasoning | Qwen3 Next / DeepSeek variants |
| Maximum capability | Frontier-tier listings |

Set `PROVER_PROVIDER=openai`, `OPENAI_BASE_URL`, `OPENAI_MODEL`, `OPENAI_API_KEY`. Set `model_card` accurately for training exports.

## vLLM

`OPENAI_BASE_URL=http://127.0.0.1:8000/v1` (or `host.docker.internal` from containers). Realign `uv run lemma meta` with the subnet.
