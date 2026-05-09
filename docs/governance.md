# Governance and upgrades

Lean verification is objective; LLM judging is subjective. Coordinate visible behavior off-chain.

## Generated templates (`LEMMA_PROBLEM_SOURCE=generated`)

Validators map block seed → theorem via [`generated.py`](../lemma/problems/generated.py). Consensus needs the same registry and release. The map is public and precomputable; [problem-supply-policy.md](problem-supply-policy.md) records that this is a supply/governance boundary, not a secrecy mechanism.

```bash
uv run lemma meta
```

Publish `generated_registry_sha256`; validators may set `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`. Difficulty mix: [generated-problems.md](generated-problems.md). Builder promotion checklist: [problem-supply-policy.md](problem-supply-policy.md).

## Frozen catalog (`LEMMA_PROBLEM_SOURCE=frozen`)

Requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (public eval catalog — not default for subnet-like traffic).

1. Build JSON ([catalog-sources.md](catalog-sources.md)).
2. Update `catalog_manifest.json`.
3. Rebuild sandbox image if toolchain pins change.
4. Tag releases and announce cutover blocks.

## Judge and rubric

Rubric: [`lemma/judge/prompts.py`](../lemma/judge/prompts.py).

```bash
uv run lemma meta
```

- `judge_rubric_sha256`: prompts only.
- `judge_profile_sha256`: validator scoring profile: judge rubric/stack plus problem cadence, verification policy, scoring blend, dedup, reputation, and response-acceptance hooks.

Production: one pinned stack; `JUDGE_PROFILE_SHA256_EXPECTED`. Dev may use multiple backends.

## Sybil and multi-account incentives

Coldkey dedup and identical-submission dedup reduce certain games but **do not** prove unique humans. Read [sybil_economics.md](sybil_economics.md) and [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml) before relying on dedup as “security.”

## Wire transport

Validator→miner calls use Bittensor Dendrite/Axon today; synapse **`body_hash`** vs **`computed_body_hash`** catches tampering — [transport.md](transport.md).

## Comparator

Experimental default-off hook ([comparator.md](comparator.md)). If an operator enables it, every scoring validator or remote Lean worker must export the same `LEMMA_COMPARATOR_*` process environment, or scores diverge.

## Shared validator settings

The **subnet operator** publishes one configuration for the subnet: timeouts, seeds, judge, sandbox image, and any experimental comparator process env. Validators are expected to deploy **that** template so scores stay comparable. Document and distribute: `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, `LEMMA_FORWARD_WAIT_MIN_S`, `LEMMA_FORWARD_WAIT_MAX_S`, `LEAN_VERIFY_TIMEOUT_S`, `LEMMA_TIMEOUT_SCALE_BY_SPLIT` / `LEMMA_TIMEOUT_SPLIT_*_MULT` (only if the operator’s policy includes them), `LEMMA_PROBLEM_SEED_MODE`, `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`, `EMPTY_EPOCH_WEIGHTS_POLICY`, `LEAN_SANDBOX_*`, `JUDGE_*`, `OPENAI_MODEL` (subnet canonical judge id on Chutes), `OPENAI_BASE_URL`, and, only if used, `LEMMA_COMPARATOR_*`. The main scoring/cadence/verification fields are pinned by `judge_profile_sha256`; comparator env is not currently pinned there. Nothing here is “per-validator preference.” On-chain code does not enforce equality — parity relies on the published policy ([faq.md](faq.md)).

### Parity checklist

1. Pin one Git tag and one immutable sandbox image ref ([toolchain-image-policy.md](toolchain-image-policy.md)).
2. Publish a shared env template.
3. Pin `uv run lemma meta`: `JUDGE_PROFILE_SHA256_EXPECTED`, optional `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED` (generated mode).
4. Announce upgrades with changelog and cutover.

Hashes reduce drift; they do not prove honest validators. Epoch tempo comes from Bittensor; forward HTTP wait per query is derived from block height and shared clamps — not a per-node dial.

## Miner axon policy

`MINER_MIN_VALIDATOR_STAKE`, permits, synapse caps — announce changes so miners are not surprised.
