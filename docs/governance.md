# Governance and upgrades

Lean verification is objective; validator scoring must stay deterministic and coordinated. Coordinate visible behavior off-chain.

## Generated templates (`LEMMA_PROBLEM_SOURCE=generated`)

Validators map block seed → theorem via [`generated.py`](../lemma/problems/generated.py). Consensus needs the same registry and release. The map is public and precomputable; [problem-supply-policy.md](problem-supply-policy.md) records that this is a supply/governance boundary, not a secrecy mechanism.

```bash
uv run lemma meta
```

Publish `generated_registry_sha256`; validators may set `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`. Difficulty mix: [generated-problems.md](generated-problems.md). Builder promotion checklist: [problem-supply-policy.md](problem-supply-policy.md).
Use the release and rotation checklist in [problem-supply-policy.md](problem-supply-policy.md#release-and-rotation-checklist) before changing the live generated registry or cadence.

## Frozen catalog (`LEMMA_PROBLEM_SOURCE=frozen`)

Requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (public eval catalog — not default for subnet-like traffic).

1. Build JSON ([catalog-sources.md](catalog-sources.md)).
2. Update `catalog_manifest.json`.
3. Rebuild sandbox image if toolchain pins change.
4. Tag releases and announce cutover blocks.

## Validator scoring profile

The validator profile covers problem cadence, verification policy, live binary scoring policy, dedup, reputation, and response-acceptance hooks.

```bash
uv run lemma meta
```

- `judge_profile_sha256`: current profile hash name for validator scoring policy.

Production: one pinned validator profile; `JUDGE_PROFILE_SHA256_EXPECTED`.
Validators should share the same reward-relevant config.

## Sybil and multi-account incentives

Coldkey dedup and identical-submission dedup reduce certain games but **do not** prove unique humans. Read [sybil_economics.md](sybil_economics.md) and [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml) before relying on dedup as “security.”

## Wire transport

Validator→miner calls use Bittensor Dendrite/Axon today; synapse **`body_hash`** vs **`computed_body_hash`** catches tampering — [transport.md](transport.md). HTTP + Epistula is a major-release migration gate, not a second default transport.

## Shared validator settings

The **subnet operator** publishes one configuration for the subnet: timeouts,
seeds, binary proof scoring policy, dedup/reputation policy, and sandbox image.
Validators are expected to deploy **that** template so scores stay comparable.
Document and distribute: `LEMMA_BLOCK_TIME_SEC_ESTIMATE`,
`LEMMA_FORWARD_WAIT_MIN_S`, `LEMMA_FORWARD_WAIT_MAX_S`,
`LEAN_VERIFY_TIMEOUT_S`, `LEMMA_TIMEOUT_SCALE_BY_SPLIT` /
`LEMMA_TIMEOUT_SPLIT_*_MULT` (only if the operator’s policy includes them),
`LEMMA_PROBLEM_SEED_MODE`, `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`,
`EMPTY_EPOCH_WEIGHTS_POLICY`, `LEAN_SANDBOX_*`, and scoring/dedup/reputation
fields. The main scoring/cadence/verification fields are pinned by
`judge_profile_sha256`. Nothing here is “per-validator preference.” On-chain
code does not enforce equality — parity relies on the published policy
([faq.md](faq.md)).

### Parity checklist

1. Pin one Git tag and one immutable sandbox image ref ([toolchain-image-policy.md](toolchain-image-policy.md)).
2. Publish a shared env template.
3. Pin `uv run lemma meta`: `JUDGE_PROFILE_SHA256_EXPECTED`, optional `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED` (generated mode).
4. Announce upgrades with changelog and cutover.

Hashes reduce drift; they do not prove honest validators. Epoch tempo comes from Bittensor; forward HTTP wait per query is derived from block height and shared clamps — not a per-node dial.

## Miner axon policy

`MINER_MIN_VALIDATOR_STAKE`, permits, synapse caps — announce changes so miners are not surprised.
