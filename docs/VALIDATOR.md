# Validator

Install → Lean image → judge keys → wallets → run.

---

## 1. Install and shell

```bash
git clone <repository-url>
cd lemma
uv sync --extra dev
source .venv/bin/activate
```

---

## 2. Base `.env`

```bash
cp .env.example .env
```

Set **`NETUID`**, **`SUBTENSOR_*`**, **`BT_WALLET_COLD`**, **`BT_WALLET_HOT`**, **`LEAN_SANDBOX_IMAGE`**, **`DENDRITE_TIMEOUT_S`**, **`EMPTY_EPOCH_WEIGHTS_POLICY`**, **`SET_WEIGHTS_*`** as needed ([`.env.example`](../.env.example)).

---

## 3. Judge API keys (interactive)

Put secrets into **`.env`** without editing keys by hand:

```bash
cd lemma
source .venv/bin/activate
lemma configure judge
```

1. Choose **openai** (OpenAI-compatible HTTP client — default stack targets Chutes / vLLM; see [MODELS.md](MODELS.md)) or **anthropic**.
2. Paste the API key when prompted (hidden).
3. Optionally set **`OPENAI_BASE_URL`** for self-hosted vLLM.

This writes **`JUDGE_PROVIDER`** and **`OPENAI_*`** or **`ANTHROPIC_*`**. Tune **`OPENAI_MODEL`**, **`JUDGE_*`** tokens/temperature in **`.env`** afterward if needed.

**Smoke without paid APIs**

```bash
export LEMMA_FAKE_JUDGE=1
lemma validator --dry-run
```

---

## 4. Lean sandbox image

```bash
cd lemma
bash scripts/prebuild_lean_image.sh
```

Point **`LEAN_SANDBOX_IMAGE`** in **`.env`** at the tag you built. From Docker to host inference, see **[MODELS.md](MODELS.md)** (**`host.docker.internal`** on macOS/Windows, bridge IP on Linux).

---

## 5. Fingerprints (subnet parity)

```bash
lemma meta
```

Publish / pin **`JUDGE_PROFILE_SHA256_EXPECTED`** if your subnet uses it ([GOVERNANCE.md](GOVERNANCE.md)).

---

## 6. Run

```bash
lemma validator --dry-run
lemma validator
```

---

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

---

## Behavior

Waits until **`blocks_until_next_epoch(netuid) <= 1`** before rounds. Prefer **`LEAN_SANDBOX_NETWORK=none`** with a warm image; use **`bridge`** only if bootstrap needs outbound network. Ops: [PRODUCTION.md](PRODUCTION.md).
