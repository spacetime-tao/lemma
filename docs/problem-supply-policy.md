# Problem Supply Policy

Lemma's default problem source is public, deterministic generated templates. This is a deliberate consensus tradeoff, not a secrecy mechanism.

## Current boundary

Generated mode maps a chain-aligned seed to one theorem with code in [`lemma/problems/generated.py`](../lemma/problems/generated.py). The SHA256 seed mix decorrelates adjacent seeds, but it does not hide the seed-to-theorem map. Anyone with the release can precompute future generated challenges once they know the relevant chain height.

That means:

- Do not describe generated templates as secret evaluation.
- Do not rely on validator-held hidden problem sets; validator secrets are expected to leak ([trust assumptions](../knowledge/trust.assumptions.yaml)).
- Do not treat SHA256 mixing as anti-precompute security.
- Do use `generated_registry_sha256` to keep validators on the same public generator.

The current generated lane is a steady traffic lane: it gives validators deterministic, Lean-checkable challenges with known template families. It is not a complete difficulty market for all of mathematics.

## Accepted risk

Public deterministic supply is acceptable only if the operator is explicit about the risk: miners may recognize repeated shapes, build warm caches, and pre-solve common families. That is not a transport or hashing bug. It is a problem-supply limitation.

Mitigation comes from breadth and governance:

- add more generated builders with varied proof shapes;
- rotate releases with announced registry hashes;
- use curated public catalog lanes only when intentionally enabled;
- later add a separate bounty/curation lane for harder formalization work.

## Builder promotion checklist

New generated builders should enter the live registry only after they pass the same checks operators expect from production traffic:

1. The statement is Lean-valid after replacing the miner proof with `sorry`.
2. At least one known proof passes the sandbox on the pinned Lean/Mathlib image.
3. The expected split is honest (`easy`, `medium`, `hard`) and not based only on proof text length.
4. Cold-cache and warm-cache verification costs fit the published timeout policy.
5. The builder has a stable source hash in `generated_registry_sha256`.
6. `docs/generated-problems.md` and operator release notes describe the changed mix.
7. Operators publish the new `generated_registry_sha256` and cutover release together.

The local/CI gate is [`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py). It always checks that every builder is reachable and has coherent registry metadata. With `RUN_DOCKER_LEAN_TEMPLATES=1`, it also materializes all generated templates into a Lean workspace and runs `lake build`.

Do not add low-value templates merely to increase the builder count. A small set of honest, varied templates is better than a large set of brittle near-duplicates.

## Frozen and curated lanes

`LEMMA_PROBLEM_SOURCE=frozen` is gated as a public eval catalog, not a hidden production source. Turning it on should be an operator decision with a release note, not a fallback path.

A future curated or bounty lane can have different cadence and incentives, but it should still avoid validator-held secrets. Prefer public formalization tasks, explicit deadlines, rollover rules, and clear reward policy over secret test-set assumptions.

## What remains open

The main unsolved work is not a code hash. It is supply design: how quickly to expand template families, when to introduce curated hard problems, and whether the subnet should reward one-off formalization bounties separately from steady generated traffic.
