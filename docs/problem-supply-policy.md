# Problem Supply Policy

Lemma's default problem source is public deterministic generated templates.

This is a consensus tradeoff. It is not secrecy.

## Current Boundary

Generated mode maps a chain-aligned seed to one theorem through
[`lemma/problems/generated.py`](../lemma/problems/generated.py).

SHA256 seed mixing reduces adjacent-seed correlation. It does not hide the
seed-to-theorem map.

Anyone with the release can precompute future generated challenges once they
know the relevant chain height.

Do:

- describe generated templates as public;
- use `generated_registry_sha256` to keep validators aligned;
- expand supply through reviewed builders and governed releases.

Do not:

- call generated templates secret evaluation;
- rely on validator-held hidden problem sets;
- treat SHA256 mixing as anti-precompute security.

## Accepted Risk

Miners may learn repeated shapes, build warm caches, and pre-solve common
families.

That is a supply limitation, not a transport bug.

Mitigation comes from:

- more varied builders;
- announced registry rotations;
- curated public catalog lanes;
- later bounty or campaign lanes.

## Builder Promotion Checklist

Add a generated builder to the live registry only when:

1. The statement is Lean-valid with the miner proof replaced by `sorry`.
2. At least one known proof passes the pinned sandbox.
3. The split label is honest: `easy`, `medium`, or `hard`.
4. Cold-cache and warm-cache costs fit timeout policy.
5. The builder changes `generated_registry_sha256`.
6. [generated-problems.md](generated-problems.md) and release notes describe the
   mix change.
7. Operators publish the new registry hash and cutover release.

Run:

```bash
uv run python scripts/ci_verify_generated_templates.py
```

With Docker Lean:

```bash
RUN_DOCKER_LEAN_TEMPLATES=1 \
  LEAN_SANDBOX_IMAGE=<immutable-image-ref> \
  uv run python scripts/ci_verify_generated_templates.py
```

Do not add low-value near-duplicates just to increase the builder count.

## Release And Rotation Checklist

Use this when changing generated builders, split mix, catalog policy, or problem
cadence.

1. Run the cheap registry/template gate.
2. Run the Docker Lean template gate when the release image is available.
3. Record old and new `generated_registry_sha256`.
4. Summarize builder counts by split.
5. Review near-duplicates.
6. Confirm verify costs fit timeout policy.
7. Announce Git tag, sandbox image ref, registry hash, and cutover block.
8. Keep the previous release runnable for rollback.

Decision record:

```text
Generated supply release:

Old registry sha:
New registry sha:
Git tag:
Sandbox image:
Cutover block/window:

Builder mix:
- easy:
- medium:
- hard:

Evidence:
- Cheap template gate:
- Docker Lean template gate:
- Verify-cost notes:
- Duplicate/near-duplicate review:

Rollback:
- Previous git tag:
- Previous sandbox image:
- Previous registry sha:
```

## Frozen And Curated Lanes

`LEMMA_PROBLEM_SOURCE=frozen` is a public eval catalog, not hidden production
supply.

Future curated, campaign, or bounty lanes can have different cadence and
incentives. They should still avoid validator-held secrets.

Use public formalization tasks, clear deadlines, rollover rules, and clear
reward policy.

Long-horizon work: [open-problem-campaigns.md](open-problem-campaigns.md).

## Open Work

The hard problem is supply design:

- how fast to add template families;
- when to introduce curated hard problems;
- whether one-off formalization bounties should be separate from generated
  traffic.
