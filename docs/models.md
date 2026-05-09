# Inference models

Lemma uses OpenAI-compatible HTTP (`/v1/chat/completions`). [Chutes](https://chutes.ai/) is the default documented host.

## What “OpenAI-compatible” means

Many providers (Chutes, **official OpenAI**, Google’s **Gemini OpenAI shim**, vLLM, LiteLLM, local gateways) expose the **same HTTP shape** that OpenAI’s Chat Completions API made standard:

- **Request:** JSON with a `model` id and a `messages` array (roles + text).
- **Response:** JSON with the assistant’s text in a **Chat Completions**-style structure.
- **Transport:** the client appends paths like **`/v1/chat/completions`** to a **base URL** you configure (e.g. `https://llm.chutes.ai/v1` or `https://api.openai.com/v1`).

So “OpenAI-compatible” is about the **wire format** (how the request/response is packed), not about which company’s *weights* you are running. The same logical model could be offered behind different bases; Lemma’s prover and judge (when `JUDGE_PROVIDER` is `chutes` or `openai`) use the **OpenAI-compatible** client path for those hosts.

**Not the same thing:** Google’s **native** Gemini REST API under `…/v1beta/models/…:generateContent` uses a **different** JSON schema (`contents` / `parts`, etc.). Lemma does **not** use that path today for the main prover; it uses the **OpenAI-compatible** base `https://generativelanguage.googleapis.com/v1beta/openai/` so the same `AsyncOpenAI` code can talk to Gemini. See Google’s [OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai) docs.

**Anthropic** is different again: it has its own API (`/v1/messages`, separate fields). That SDK is an optional install: use `uv sync --extra anthropic` when `PROVER_PROVIDER=anthropic` or local judge tooling uses `JUDGE_PROVIDER=anthropic`.

Interactive setup (`lemma-cli configure judge` / `configure prover`): reply with a **row number** or the **backend keyword** (`chutes`, `gemini`, …). For **`lemma-cli configure prover`**, you **pick the vendor first** (Chutes, Gemini, Anthropic, hosted OpenAI, or custom OpenAI-compat URL); the next prompts ask for API keys and **`PROVER_MODEL`** (with dim examples in-terminal — preset tiers for Gemini, defaults for Chutes/Anthropic, required string for OpenAI, provider-specific id for custom).

## Catalog

```bash
curl -sS https://llm.chutes.ai/v1/models | jq '.data[] | {id, pricing}'
```

Use `id` as `OPENAI_MODEL`.

## Validators (judge)

**Required** for `lemma validator start`: `JUDGE_PROVIDER=chutes`, `OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2-TEE`, and `OPENAI_BASE_URL=https://llm.chutes.ai/v1` — no self-hosted or alternate judge stack for scoring (`openai` remains a legacy alias for the same HTTP client path). Set **`JUDGE_OPENAI_API_KEY`** to your Chutes inference token (or legacy **`OPENAI_API_KEY`** if you keep a single judge key there). Miners use `PROVER_*` and may call any prover model the operator runs.

One pinned validator scoring profile per subnet: `uv run lemma meta` → `judge_profile_sha256` → optional `JUDGE_PROFILE_SHA256_EXPECTED`. This includes the judge stack and the deterministic scoring/cadence/verification knobs that affect weights.

Judge emits short JSON. After changing endpoints, models, scoring knobs, problem cadence, or verifier policy, rerun `uv run lemma meta` and redistribute hashes.

## Miners (prover)

Use a **reasoning-capable** model that writes valid `Submission.lean`. Recommended baseline on Chutes: the same family as the subnet judge (`deepseek-ai/DeepSeek-V3.2-TEE`) or another strong reasoning model you operate reliably.

| Goal | Examples |
| ---- | -------- |
| Align with subnet judge tier | `deepseek-ai/DeepSeek-V3.2-TEE` |
| Other reasoning options | Other DeepSeek / Qwen / frontier reasoning listings on Chutes |

Set `PROVER_PROVIDER=openai`, **`PROVER_OPENAI_BASE_URL`** (or rely on judge `OPENAI_BASE_URL` if unset), **`PROVER_OPENAI_API_KEY`** (or legacy `OPENAI_API_KEY` fallback), and **`PROVER_MODEL`** (miner-only id; falls back to `OPENAI_MODEL` if unset). Optional `model_card` for training exports.

The live miner (`lemma miner start`) starts solving **as soon as** a validator forwards a challenge — no deliberate wait for block ticks. `lemma-cli try-prover` is separate (manual smoke test).

Custom **`PROVER_OPENAI_BASE_URL`** / keys for the **prover** are normal (any OpenAI-compatible host you operate). The **subnet judge** for validators stays on the pinned Chutes stack above—self-hosted judge endpoints are not the default production path.

Anthropic prover support is optional. Install it with `uv sync --extra anthropic`, then set `PROVER_PROVIDER=anthropic`, `ANTHROPIC_API_KEY`, and `PROVER_MODEL` or `ANTHROPIC_MODEL`.
