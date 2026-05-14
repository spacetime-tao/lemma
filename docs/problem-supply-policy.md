# Problem Supply Policy

Lemma's default problem source is public, deterministic hybrid supply: generated templates plus a curated catalog lane. This is a deliberate consensus tradeoff, not a secrecy mechanism.

## Current boundary

Hybrid mode maps a chain-aligned seed to one theorem using code in [`lemma/problems/hybrid.py`](../lemma/problems/hybrid.py), generated builders in [`lemma/problems/generated.py`](../lemma/problems/generated.py), and the bundled curated pack in [`lemma/problems/curated_catalog.json`](../lemma/problems/curated_catalog.json). SHA256 seed mixing decorrelates adjacent seeds, but it does not hide the seed-to-theorem map. Anyone with the release can precompute future challenges once they know the relevant chain height.

That means:

- Do not describe hybrid supply or generated templates as secret evaluation.
- Do not rely on validator-held hidden problem sets; validator secrets are expected to leak ([trust assumptions](../knowledge/trust.assumptions.yaml)).
- Do not treat SHA256 mixing as anti-precompute security.
- Do use `problem_supply_registry_sha256` to keep validators on the same public hybrid supply.
- Do treat registry hashes as alignment fingerprints, not as proof that the
  supply is mathematically broad, bug-free, licensed, or faithful to any
  informal source.

The current hybrid lane is steady traffic: deterministic, Lean-checkable challenges with known generated families and a reviewed curated catalog. The generated registry has 100 builders and explicit 10% / 35% / 50% / 5% easy / medium / hard / extreme split weights; hybrid source weights default to 60% generated and 40% catalog. Extreme is a rare stretch tier inside steady cadence, not the off-cadence bounty/campaign lane.

Known-solution cadence is the right foundation. It lets miners build proof
capacity against statements that are guaranteed to be provable, lets validators
keep the reward axis binary, and avoids dead rounds where no participant can
reasonably know whether the target is reachable. Formalized open conjectures are
valuable future work, but they belong in an off-cadence campaign or bounty lane
after statement faithfulness review.

## Accepted risk

Public deterministic supply is acceptable only if the operator is explicit about the risk: miners may recognize repeated shapes, build warm caches, and pre-solve common families. The curated lane increases breadth; it is still public supply, not hidden evaluation.

Mitigation comes from breadth and governance:

- add more generated builders with varied proof shapes;
- add reviewed curated catalog rows with authored informal statements;
- rotate releases with announced registry hashes;
- use curated public catalog lanes only when intentionally enabled;
- later add a separate bounty/curation lane for harder formalization work.

The first normal-cadence expansion should prioritize generated builders over
external dataset imports. Good next topics are Euclidean geometry-lite,
probability and expectation, calculus basics, finite and infinite series, real
graph theory, stronger modular or Diophantine number theory, and harder
inequality schemas. Each new family should add a genuinely new proof shape, not
just another constant swap around an existing tactic exercise.

## Builder promotion checklist

New generated builders should enter the live registry only after they pass the same checks operators expect from production traffic:

1. The statement is Lean-valid after replacing the miner proof with `sorry`.
2. At least one public witness proof passes the sandbox on the pinned Lean/Mathlib image and axiom check.
3. The expected split is honest (`easy`, `medium`, `hard`, `extreme`) and not based only on proof text length.
4. Cold-cache and warm-cache verification costs fit the published timeout policy.
5. The builder has a stable source hash in `generated_registry_sha256`.
6. `docs/generated-problems.md` and operator release notes describe the changed mix.
7. Operators publish the new `generated_registry_sha256` and cutover release together.

The local/CI gate is [`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py). It always checks that every builder is reachable and has coherent registry metadata, an authored `informal_statement`, and a public witness proof. With `RUN_DOCKER_LEAN_TEMPLATES=1`, it also materializes all generated templates into Lean workspaces and runs both the `sorry` stub build and the complete witness-proof build with axiom checks.

Do not add low-value templates merely to increase the builder count. A small set of honest, varied templates is better than a large set of brittle near-duplicates.

## External source promotion

External contest or benchmark sources such as miniF2F-style repositories,
Compfiles, PutnamBench, FormalMATH, or mathlib samples can improve breadth, but
they should not enter live `hybrid` supply until source review is complete.

Before promotion, record:

- upstream repository or dataset name;
- exact commit, release, or dataset revision;
- license and attribution requirements;
- whether the row is solved, unsolved, training, validation, or test material;
- whether the statement has a complete witness proof under Lemma's pinned
  Lean/Mathlib toolchain;
- whether the statement is appropriate for normal cadence or belongs in a
  campaign/bounty lane instead.

The current default live supply does not depend on imported miniF2F or Putnam
rows. Generated builders are repo-authored templates with witness proofs, and
the bundled curated catalog is a small reviewed live pack with authored public
statements. The frozen/import tooling is useful for development and future
catalog construction, not an automatic production source.

## Release and rotation checklist

Use this when changing generated builders, split mix, catalog policy, or problem
cadence. The point is to make supply changes explicit, not to pretend a new hash
is a new security model.

1. Run the cheap registry/template gate:

   ```bash
   uv run python scripts/ci_verify_generated_templates.py
   ```

2. If the sandbox image for the release is available, run the Lean template gate:

   ```bash
   RUN_DOCKER_LEAN_TEMPLATES=1 \
     LEAN_SANDBOX_IMAGE=<immutable-image-ref> \
     uv run python scripts/ci_verify_generated_templates.py
   ```

3. Record the old and new `problem_supply_registry_sha256` and `generated_registry_sha256` from `uv run lemma meta`.
4. Record the new `validator_profile_sha256` from `uv run lemma meta`.
5. Summarize the old and new builder counts by split.
6. Check whether any new builder family is a near-duplicate of an existing one.
7. Confirm verification costs fit the published timeout policy.
8. Announce the Git tag, immutable sandbox image ref, registry hashes, validator
   profile hash, and cutover block/window together.
9. Keep the previous release runnable long enough for rollback.

Decision record shape:

```text
Generated supply release:

Old registry sha:
New problem supply sha:
New generated registry sha:
Validator profile sha:
Git tag:
Sandbox image ref:
Lean toolchain:
Mathlib revision:
Cutover block/window:

Builder mix:
- easy:
- medium:
- hard:
- extreme:
- split weights:

Evidence:
- Cheap template gate:
- Docker Lean template gate:
- Docker witness-proof gate:
- Verify-cost notes:
- Duplicate/near-duplicate review:

Rollback:
- Previous git tag:
- Previous sandbox image:
- Previous problem supply sha:
- Previous generated registry sha:
- Previous validator profile sha:
```

## Frozen and curated lanes

`LEMMA_PROBLEM_SOURCE=frozen` is gated as a public eval catalog, not a hidden production source. Turning it on should be an operator decision with a release note, not a fallback path.

A future curated, campaign, or bounty lane can have different cadence and incentives, but it should still avoid validator-held secrets. Prefer public formalization tasks, explicit deadlines, rollover rules, and clear reward policy over secret test-set assumptions. Longer-horizon open-problem work is tracked separately in [open-problem-campaigns.md](open-problem-campaigns.md).

## What remains open

The main unsolved work is not a code hash. It is supply design: how quickly to expand template families, when to introduce curated hard problems, and whether the subnet should reward one-off formalization bounties separately from steady generated traffic.
