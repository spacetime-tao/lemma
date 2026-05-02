# Governance and upgrades

Lemma separates **Lean verification** (objective) from **LLM judging** (subjective). Visible behavior changes should be coordinated off-chain.

## Generated templates (`LEMMA_PROBLEM_SOURCE=generated`)

Validators map each block seed to one theorem via [`generated.py`](../lemma/problems/generated.py). Consensus requires the **same** registry (`TOPICS`, `_RAW_BUILDERS`) and release.

```bash
uv run lemma meta
```

Publish **`generated_registry_sha256`**; validators may set **`LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`** to reject mismatched deployments.

Difficulty mix and timeouts: [GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md).

## Frozen catalog (`LEMMA_PROBLEM_SOURCE=frozen`)

1. Build JSON ([CATALOG_SOURCES.md](CATALOG_SOURCES.md)).
2. Update **`catalog_manifest.json`**.
3. Rebuild sandbox image if toolchain pins change.
4. Tag releases and announce cutover blocks.

## Judge and rubric

Rubric text: [`lemma/judge/prompts.py`](../lemma/judge/prompts.py).

```bash
uv run lemma meta
```

- **`judge_rubric_sha256`**: prompts only.
- **`judge_profile_sha256`**: prompts + provider + model + sampling + (for OpenAI-compatible) base URL.

Validators should run **one** pinned configuration; use **`JUDGE_PROFILE_SHA256_EXPECTED`**.

The codebase supports multiple judge backends for development; production subnets should standardize one stack.

## Comparator

Optional binary hook ([COMPARATOR.md](COMPARATOR.md)). If any validator enables it, **all** must share **`LEMMA_COMPARATOR_CMD`** or weights diverge.

## Shared validator settings

Document **`DENDRITE_TIMEOUT_S`**, **`LEAN_VERIFY_TIMEOUT_S`**, **`LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`** (same **`N`** across validators), **`EMPTY_EPOCH_WEIGHTS_POLICY`**, **`LEAN_SANDBOX_*`**, **`JUDGE_*`**, **`OPENAI_*`**, **`LEMMA_COMPARATOR_*`**. **`DENDRITE_TIMEOUT_S`** should match across validators (not enforced on-chain).

### Parity checklist

1. Pin one Git tag / image digest.
2. Publish a shared env template.
3. Pin **`uv run lemma meta`** outputs: **`JUDGE_PROFILE_SHA256_EXPECTED`**, optional **`LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`** (generated mode).
4. Announce upgrades with changelog and cutover timing.

Profile hashes reduce accidental drift; they do not cryptographically prove honest validators.

**Epoch tempo** comes from Bittensor subnet parameters. **`DENDRITE_TIMEOUT_S`** only bounds each miner HTTP response.

## Miner axon policy

`MINER_MIN_VALIDATOR_STAKE`, permits, and synapse caps are operational knobs; announce changes to avoid unexpected HTTP errors.
