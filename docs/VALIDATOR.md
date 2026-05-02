# Validator

Walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md) — `lemma setup` (validator or both) sets judge and `LEAN_SANDBOX_IMAGE` via prompts.

Default: new round every `LEMMA_VALIDATOR_ROUND_INTERVAL_S` (300 s). Set `LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH=1` for epoch-bound cadence.

Judge: Chutes when prompted is the documented default; Anthropic and custom OpenAI-compatible URLs optional.

## Lean image

```bash
bash scripts/prebuild_lean_image.sh
./scripts/lemma-run lemma validator --dry-run
./scripts/lemma-run lemma validator
```

Local smoke without LLM cost: `export LEMMA_FAKE_JUDGE=1`.

## Fingerprints

```bash
./scripts/lemma-run lemma meta
```

[GOVERNANCE.md](GOVERNANCE.md).

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

## Ops

[PRODUCTION.md](PRODUCTION.md).
