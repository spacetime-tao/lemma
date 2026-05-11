# Governance And Upgrades

Lean verification is objective. Validator scoring still needs shared releases
and shared settings.

## Generated Templates

With `LEMMA_PROBLEM_SOURCE=generated`, validators map block seed to theorem
through [`generated.py`](../lemma/problems/generated.py).

This map is public and precomputable. That is a known problem-supply boundary,
not a secrecy feature.

Before changing the live generated registry or cadence, use the checklist in
[problem-supply-policy.md](problem-supply-policy.md#release-and-rotation-checklist).

Publish the generated registry hash:

```bash
uv run lemma meta
```

Validators may set:

```text
LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED
```

## Frozen Catalog

`LEMMA_PROBLEM_SOURCE=frozen` is for public eval catalog use. It requires:

```text
LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1
```

When changing frozen catalogs:

1. Build JSON.
2. Update `catalog_manifest.json`.
3. Rebuild the sandbox image if toolchain pins change.
4. Tag the release and announce the cutover.

## Validator Profile

The validator profile covers reward-relevant settings:

- problem cadence;
- verification policy;
- proof scoring;
- same-coldkey partitioning;
- reputation;
- response hooks.

Run:

```bash
uv run lemma meta
```

Share `validator_profile_sha256`. Production validators should use the same
profile and may set `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED`.

## Shared Settings

The subnet operator should publish one env template for:

- timeouts;
- seed mode;
- problem cadence;
- proof scoring;
- partition and reputation policy;
- sandbox image;
- empty-epoch policy.

These are subnet policy, not per-validator preferences.

## Parity Checklist

1. Pin one Git tag.
2. Pin one immutable sandbox image ref.
3. Publish one env template.
4. Publish `validator_profile_sha256`.
5. Publish `generated_registry_sha256` when generated mode is used.
6. Announce upgrades with a changelog and cutover.

Hashes reduce drift. They do not prove validators are honest.

## Sybil And Multi-Account Notes

Same-coldkey partitioning does not prove unique humans.

Read [sybil_economics.md](sybil_economics.md) and
[`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml) before
treating coldkeys as identity.

## Transport

Lemma uses Bittensor Dendrite/Axon today. Synapse body-hash checks catch many
transport mismatches.

HTTP plus Epistula would be a major migration, not a small setting change. See
[transport.md](transport.md).

## Miner Axon Policy

Announce changes to:

- `MINER_MIN_VALIDATOR_STAKE`;
- permit rules;
- synapse caps;
- forward wait policy.
