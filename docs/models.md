# Inference Models

Miners use a prover model to write Lean. Validators do not need an inference
model to check proofs.

Lemma's prover client uses OpenAI-compatible HTTP at `/v1/chat/completions`.

## What OpenAI-Compatible Means

OpenAI-compatible means the request and response use the Chat Completions shape:

- request: `model` plus `messages`;
- response: assistant text in a Chat Completions-style object;
- base URL: the client appends `/v1/chat/completions`.

This describes the wire format, not the company running the model.

Examples include Chutes, OpenAI, Gemini's OpenAI-compatible endpoint, vLLM,
LiteLLM, and custom gateways.

Gemini's native `generateContent` API is different. Lemma uses Gemini through
Google's OpenAI-compatible base URL.

Anthropic uses a different API. Install it with:

```bash
uv sync --extra anthropic
```

## Setup

Use the wizard:

```bash
uv run lemma-cli configure prover
```

Pick a provider, enter the API key, and choose `PROVER_MODEL`.

For OpenAI-compatible providers, set:

- `PROVER_PROVIDER=openai`
- `PROVER_OPENAI_BASE_URL`
- `PROVER_OPENAI_API_KEY`
- `PROVER_MODEL`

`OPENAI_API_KEY` and `OPENAI_MODEL` are legacy fallbacks.

## Chutes Catalog

```bash
curl -sS https://llm.chutes.ai/v1/models | jq '.data[] | {id, pricing}'
```

Use the returned `id` as `PROVER_MODEL`.

## Validators

Validators need:

- pinned Lean sandbox;
- verifier policy;
- problem cadence;
- proof-scoring policy.

They do not need a prover model for proof scoring.

After changing verifier or scoring policy, run:

```bash
uv run lemma meta
```

Share the new `validator_profile_sha256` with validators. Operators may set
`LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED` to fail fast on drift.

## Miners

Use a model that reliably writes valid `Submission.lean`.

The live miner starts solving as soon as a validator forwards a challenge. It
does not wait for block ticks.

`uv run lemma-cli try-prover` is only a manual smoke test.

For Anthropic:

```bash
uv sync --extra anthropic
```

Then set:

- `PROVER_PROVIDER=anthropic`
- `ANTHROPIC_API_KEY`
- `PROVER_MODEL` or `ANTHROPIC_MODEL`
