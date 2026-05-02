# Subnet governance / upgrades

Lemma splits **objective** verification (Lean in Docker) from **subjective** judging (LLM rubric). Operators should coordinate off-chain and via subnet docs whenever behavior-visible artifacts change.

## Generated templates (`LEMMA_PROBLEM_SOURCE=generated`, default)

Validators expand each epoch’s block seed into **one** theorem using [`lemma/problems/generated.py`](../lemma/problems/generated.py). **Consensus requires identical code:** same Git release (or Docker image digest), same `LEMMA_PROBLEM_SOURCE`, and the same ordered template registry (`TOPICS` + `_RAW_BUILDERS`). Changing templates is a **subnet upgrade**—announce it like a catalog bump.

Fingerprints (share off-chain like the judge profile):

```bash
uv run lemma meta
# prints generated_registry_sha256=... and generated_registry_json=...
```

Set **`LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`** to that value so a validator **refuses to start** if someone deploys the wrong revision by mistake (same idea as **`JUDGE_PROFILE_SHA256_EXPECTED`**).

**What miners see (difficulty mix, timeouts, “why this subnet”):** see [GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md).

## Catalog bumps (`minif2f_frozen.json`, frozen mode only)

Use this path only when **`LEMMA_PROBLEM_SOURCE=frozen`**. Otherwise see **Generated templates** above.

1. Build the frozen catalog, e.g. `python scripts/build_lemma_catalog.py --out lemma/problems/minif2f_frozen.json --sources yangky,dm,putnam` or `python scripts/load_minif2f.py` for a single miniF2F-lean4 snapshot (see [CATALOG_SOURCES.md](CATALOG_SOURCES.md)).
2. Confirm `lemma/problems/catalog_manifest.json` matches (problem_count, ref); the loader overwrites the manifest next to the catalog.
3. **Rebuild** the Lean sandbox image if `lean_toolchain` / `mathlib_rev` in rows changed (`compose/lean.Dockerfile`).
4. Tag a release (Git tag + changelog). Announce **block height or epoch** from which validators must switch so miners are not surprised.

## Judge / rubric changes

Rubric text lives in `lemma/judge/prompts.py`. Canonical fingerprints:

```bash
uv run lemma meta
# prints problem_source=..., generated_registry_* (generated mode), judge_rubric_sha256=..., judge_profile_sha256=..., ...
```

- **`judge_rubric_sha256`** — hash of rubric prompts only (upgrade when `prompts.py` changes).
- **`judge_profile_sha256`** — hash of rubric + active provider + model + sampling params + (for `openai`) `OPENAI_BASE_URL`. Use this to pin **one** judge stack across validators (including self-hosted open weights behind an OpenAI-compatible API).

Subnet operators should agree on **one** configuration and publish **`judge_profile_sha256`** (and Docker/git tags they run). Validators can set **`JUDGE_PROFILE_SHA256_EXPECTED`** to that value so the process **exits immediately** if env drifts (wrong model, URL, temperature, or rubric).

### Open-source judge model (recommended pattern)

Affine-style fairness needs **one** grading model everyone uses; Lemma does not ship a specific checkpoint — operators choose an instruct model and serve it consistently:

1. Pick **one** open-weight instruct model and **one** serving stack (e.g. [vLLM](https://github.com/vllm-project/vllm) OpenAI server).
2. Defaults ship as **`JUDGE_PROVIDER=openai`**, **`OPENAI_MODEL=Qwen/Qwen3-32B-TEE`**, **`OPENAI_BASE_URL=https://llm.chutes.ai/v1`** (Chutes). Override when switching stacks (e.g. self-hosted vLLM); **`OPENAI_API_KEY`** is whatever the host requires (Chutes API key or a placeholder locally).
3. Align **`JUDGE_TEMPERATURE`** / **`JUDGE_MAX_TOKENS`** subnet-wide.
4. Run **`uv run lemma meta`** on a reference machine, distribute **`judge_profile_sha256`** + **`judge_profile_json`**, set **`JUDGE_PROFILE_SHA256_EXPECTED`** on each validator.

**Tamper resistance** is operational: you cannot prove a remote validator runs unmodified code from the chain alone. Mitigations are **reproducible releases** (pinned Git tag + Docker image digest), **published constitution** (profile hash + subnet announcement), and **social verification**. The profile hash catches accidental misconfiguration; deliberate cheating is an incentive / monitoring problem outside this repo.

### Why the code allows more than one judge “brand” (Anthropic vs OpenAI)

The implementation supports **two API shapes** so teams can develop and dry-run with whatever keys they have. **On a live subnet, you should not treat that as “each validator picks a favorite model.”** Fairness requires **one** provider + **one** model (or one self-hosted endpoint) + **one** temperature/max-tokens policy, then **`JUDGE_PROFILE_SHA256_EXPECTED`** so misconfigured validators stop immediately. Different validators running different judges ⇒ incomparable scores and easy governance fights—exactly what **`lemma meta`** + the profile hash are meant to prevent.

### Comparator hook vs uniformity

**Lean** already gives a strict pass/fail on proofs and axioms. An optional **comparator** ([COMPARATOR.md](COMPARATOR.md)) is for **extra** checks some subnets may adopt (e.g. stronger statement equivalence). If **any** validator enables it, **all** validators on that subnet should use the **same** `LEMMA_COMPARATOR_CMD` (or **none**), or weights become incomparable—same logic as the judge. It is not on by default because wiring is deployment-specific and adds ops burden.

Treat rubric or judge profile changes like a **consensus upgrade**: document, version, and align timing with other operators.

## Validator settings

Document and share: `DENDRITE_TIMEOUT_S`, `EMPTY_EPOCH_WEIGHTS_POLICY` (`skip` vs `uniform`), `LEAN_VERIFY_TIMEOUT_S`, and weight-retry env vars. **`DENDRITE_TIMEOUT_S` should match across validators** (Lemma does not enforce it on-chain); divergence changes who times out and is unfair. Other divergent values do not break the chain but **do** change who gets credit in an epoch.

### Keeping every validator on the same Lemma (parity checklist)

Lemma **cannot** cryptographically prove two remote validators run identical code; alignment is **operations + hashes**. Subnet operators typically:

1. **Pin one release** — same **Git tag** (and ideally same **Docker image digest** if you ship containers). Everyone deploys from that artifact only.
2. **Publish one env template** — a subnet-managed `.env` or matrix that fixes **`LEMMA_PROBLEM_SOURCE`**, **`DENDRITE_TIMEOUT_S`**, **`LEAN_VERIFY_TIMEOUT_S`**, **`LEAN_SANDBOX_*`**, **`JUDGE_*`**, **`OPENAI_*`**, optional **`LEMMA_COMPARATOR_*`**, and **`EMPTY_EPOCH_WEIGHTS_POLICY`**. Treat drift like a bug.
3. **Pin hashes from `uv run lemma meta`** on that release branch:
   - **`JUDGE_PROFILE_SHA256_EXPECTED`** — same judge model, URL, temperature, max tokens, rubric.
   - **`LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`** when using **generated** templates (same `generated.py` registry).
4. **Announce upgrades** — changelog + “cutover” note so all validators bump together; miners see fewer inconsistent rounds.
5. **Detect mistakes** — optional CI on the repo tag that runs **`uv run lemma meta`** and fails if outputs drift from published JSON; community monitoring if a validator’s weights look uncorrelated (social layer).

**What this does *not* solve:** a malicious validator could still run different software off-chain. Mitigations are **stake / reputation**, **open-source audits**, and **economic incentives** — same as other subnets. The hashes mainly stop **accidental** misconfiguration.

**How long miners get for one answer:** `DENDRITE_TIMEOUT_S` is the **HTTP deadline for one challenge** (validator → miner round-trip). Raising it gives miners more wall-clock time per proof **without** changing how often the chain runs scoring epochs—that tempo is a **Bittensor subnet / hyperparameter** matter (see [Bittensor docs — Managing subnets](https://docs.learnbittensor.org/) and subnet hyperparameters). Different subnets (e.g. incentive designs like Affine) pick different schedules and evaluation rules; Lemma still uses its own protocol but inherits **epoch timing** from the chain.

## Miner policy

`MINER_MIN_VALIDATOR_STAKE`, `MINER_REQUIRE_VALIDATOR_PERMIT`, and payload caps are **defense in depth** for the axon. Changes should be announced so miners do not get spurious 403/413 errors.
