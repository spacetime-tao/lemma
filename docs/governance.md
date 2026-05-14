# Governance and upgrades

Lean verification is objective; validator scoring must stay deterministic and coordinated. Coordinate visible behavior off-chain.

## Hybrid problem supply (`LEMMA_PROBLEM_SOURCE=hybrid`)

Validators map block seed → theorem via [`hybrid.py`](../lemma/problems/hybrid.py), generated builders, and the curated catalog pack. Consensus needs the same registry, weights, catalog, and release. The map is public and precomputable; [problem-supply-policy.md](problem-supply-policy.md) records that this is a supply/governance boundary, not a secrecy mechanism.

```bash
uv run lemma meta
```

Publish `problem_supply_registry_sha256`; validators set `LEMMA_PROBLEM_SUPPLY_REGISTRY_SHA256_EXPECTED`. The current hybrid source defaults to 60% generated templates and 40% curated catalog rows. The generated registry has 100 builders with explicit 10% / 35% / 50% / 5% easy / medium / hard / extreme split weights. Difficulty mix: [generated-problems.md](generated-problems.md). Builder/catalog promotion checklist: [problem-supply-policy.md](problem-supply-policy.md).
Use the release and rotation checklist in [problem-supply-policy.md](problem-supply-policy.md#release-and-rotation-checklist) before changing the live supply, generated registry, catalog, weights, or cadence.

Registry hashes are coordination fingerprints. They prove validators are aligned
to the same release surface; they do not prove the problem supply is high
quality, licensed correctly, or mathematically faithful. Quality still comes
from review, witness proofs, Docker Lean gates, and release discipline.

## Generated templates only (`LEMMA_PROBLEM_SOURCE=generated`)

Generated-only mode remains available for rollback or focused testing. Validators in this mode pin `generated_registry_sha256` with `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`.

## Frozen catalog (`LEMMA_PROBLEM_SOURCE=frozen`)

Requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (public eval catalog — not default for subnet-like traffic).

1. Build JSON ([catalog-sources.md](catalog-sources.md)).
2. Update `catalog_manifest.json`.
3. Rebuild sandbox image if toolchain pins change.
4. Tag releases and announce cutover blocks.

## Validator scoring profile

The validator profile covers problem cadence, verification policy, live proof scoring policy, same-coldkey partitioning, reputation, and response-acceptance hooks.

```bash
uv run lemma meta
```

- `validator_profile_sha256`: current profile hash name for validator scoring policy.

Production: one pinned validator profile; `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED`.
Validators should share the same reward-relevant config.

## Sybil and multi-account incentives

Same-coldkey partitioning does **not** prove unique humans. Read [sybil_economics.md](sybil_economics.md) and [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml) before treating coldkeys as identity.

## Wire transport

Validator→miner calls use Bittensor Dendrite/Axon today; synapse **`body_hash`** vs **`computed_body_hash`** catches tampering — [transport.md](transport.md). HTTP + Epistula is a major-release migration gate, not a second default transport.

## Shared validator settings

The **subnet operator** publishes one configuration for the subnet: timeouts,
seeds, proof-verification scoring policy, rolling-score/partition policy, and sandbox image.
Validators are expected to deploy **that** template so scores stay comparable.
Document and distribute: `LEMMA_BLOCK_TIME_SEC_ESTIMATE`,
`LEMMA_FORWARD_WAIT_MIN_S`, `LEMMA_FORWARD_WAIT_MAX_S`,
`LEAN_VERIFY_TIMEOUT_S`, `LEMMA_TIMEOUT_SCALE_BY_SPLIT` /
`LEMMA_TIMEOUT_SPLIT_*_MULT` (only if the operator’s policy includes them),
`LEMMA_PROBLEM_SEED_MODE`, `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS`,
`LEAN_SANDBOX_*`, and scoring/partition fields. The main
scoring/cadence/verification fields are pinned by
`validator_profile_sha256`. Nothing here is “per-validator preference.” On-chain
code does not enforce equality — parity relies on the published policy
([technical-reference.md](technical-reference.md)).

### Parity checklist

1. Pin one Git tag and one immutable sandbox image ref ([toolchain-image-policy.md](toolchain-image-policy.md)).
2. Publish a shared env template.
3. Pin `uv run lemma meta`: `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED` and `LEMMA_PROBLEM_SUPPLY_REGISTRY_SHA256_EXPECTED` (hybrid mode).
4. Announce upgrades with changelog and cutover.

Hashes reduce drift; they do not prove honest validators. Epoch tempo comes from Bittensor; forward HTTP wait per query is derived from block height and shared clamps — not a per-node dial.

## Trust-minimized release evidence

Every live rollout should publish enough evidence for another operator to
reproduce the verifier and compare config:

- Git commit and release tag;
- sandbox image immutable ref, preferably a digest;
- Lean toolchain and Mathlib revision;
- `validator_profile_sha256`;
- `problem_supply_registry_sha256`;
- `generated_registry_sha256`;
- generated-builder split counts and hybrid lane weights;
- generated-template metadata gate result;
- Docker Lean stub and witness gate result;
- cutover block/window and rollback release.

Future public-verification logs should make individual rounds rerunnable by
recording theorem id, theorem statement, submitted proof or proof digest,
registry/profile hashes, verifier image ref, and verification result. Avoid
adding protocol machinery until the minimal public evidence format is clear.

## Config drift detection

Operators can already compare `lemma meta --raw` output against published pins.
The next trust-minimization step is to make drift easier to spot: a compact
health/report command should print the deployed commit, sandbox image ref,
profile hash, problem-supply hash, generated-registry hash, current problem
source, latest epoch summary, and set-weights status.

## Miner axon policy

`MINER_MIN_VALIDATOR_STAKE`, permits, synapse caps — announce changes so miners are not surprised.
