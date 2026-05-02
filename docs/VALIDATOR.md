# Validator

Full walkthrough: [GETTING_STARTED.md](GETTING_STARTED.md) — **`lemma setup`** (role **validator** or **both**) configures judge + **`LEAN_SANDBOX_IMAGE`** via prompts (no manual **`.env`** edits).

**Judge inference:** Chutes is recommended when prompted; Anthropic and custom OpenAI-compatible URLs are optional.

---

## Lean image

```bash
cd lemma
bash scripts/prebuild_lean_image.sh
```

Then:

```bash
./scripts/lemma-run lemma validator --dry-run
./scripts/lemma-run lemma validator
```

**Smoke without LLM spend:** **`export LEMMA_FAKE_JUDGE=1`** for local checks only.

---

## Fingerprints

```bash
./scripts/lemma-run lemma meta
```

[GOVERNANCE.md](GOVERNANCE.md).

---

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

---

## Behavior + ops

[PRODUCTION.md](PRODUCTION.md).
