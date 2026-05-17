# Upstream Publication

Lemma should close the loop with Google DeepMind's public Formal Conjectures corpus.

A solved theorem should not disappear into reward accounting. After a proof passes Lean and receives the required subnet attestation, Lemma can publish a canonical proof artifact and prepare an upstream contribution candidate for the source repository when appropriate.

For Formal Conjectures targets, the normal upstream candidate is a small pull request that marks the statement as solved and links to the Lemma proof artifact.

## Why This Exists

The public output of Lemma is not only a bounty claim. It is a growing record of mechanically checked proof work.

Upstream publication makes solved targets:

- discoverable outside the subnet,
- reviewable by humans,
- useful to automated theorem proving benchmarks,
- traceable to source statements and solver provenance,
- reusable by the wider Lean and mathematics communities.

## Scope

Upstream publication applies to targets with enough source metadata to identify the upstream declaration.

For a Formal Conjectures target, the registry should include:

- upstream repository,
- upstream commit,
- file path,
- declaration name,
- original category,
- known `formal_proof` metadata if present,
- target hash,
- toolchain id,
- mathlib revision.

If that metadata is missing, Lemma can still verify and reward a target under its own rules, but no publication sidecar should open an upstream PR automatically.

## Lifecycle

A solved target can move through these publication states:

| State | Meaning |
| --- | --- |
| `verified` | Lean accepted the submitted proof for the exact theorem. |
| `attested` | Validator attestation threshold or subnet rule has been met. |
| `settled` | Reward custody path has completed or the proof is reward-eligible under the active rules. |
| `artifact_published` | Canonical proof artifact is publicly available. |
| `pr_prepared` | A patch and PR body were generated for human review. |
| `pr_opened` | A pull request was opened against the upstream repository. |
| `upstream_merged` | Upstream maintainers accepted the contribution. |
| `upstream_closed` | The PR was closed, superseded, or rejected. |

These states are documentation guidance for the publication process. They are not a new protocol API in this pass.

## Settlement Is Independent From Upstream Acceptance

Reward settlement must not depend on GitHub, Google DeepMind, or upstream maintainers accepting a PR.

Lemma settlement depends on the published target, the verifier result, and the subnet reward rules. The upstream PR is a publication and review path after the proof has been verified and attested.

This separation is important because upstream maintainers may reject or request changes for reasons outside Lemma's reward boundary, including:

- formalization mismatch,
- style preferences,
- missing references,
- missing CLA status,
- upstream repository policy,
- duplicate or superseded work,
- a stronger proof artifact becoming available.

## Formal Conjectures PR Shape

For a Formal Conjectures target that was originally tagged as open, the generated PR should usually be minimal:

1. Change `@[category research open]` to `@[category research solved]`.
2. Add `formal_proof using lean4 at "<artifact-url>"` to the attribute list.

Example:

```lean
-- Before
@[category research open, AMS 11]
theorem some_problem : SomeStatement := by
  sorry

-- After
@[category research solved, AMS 11, formal_proof using lean4 at "https://lemmasub.net/proofs/<claim-id>"]
theorem some_problem : SomeStatement := by
  sorry
```

The PR should not usually paste the entire proof into Formal Conjectures unless upstream maintainers request it. Formal Conjectures supports linking to proofs hosted elsewhere through the `formal_proof` mechanism.

## PR Package

Until artifact hosting and automation are proven, default to a human-reviewed PR package instead of auto-opening PRs.

A package should include:

```text
upstream-pr/
  patch.diff
  PR_BODY.md
  artifact.json
  Submission.lean
  verifier.json
```

The PR body should include:

- artifact URL,
- Lemma target id,
- source commit, file, and declaration,
- target hash,
- submission hash,
- toolchain and mathlib revision,
- verifier id,
- attestation id or summary,
- independence notice.

## Affiliation Notice

Use this text in docs and PR bodies:

> Lemma is independent and is not endorsed by Google DeepMind or the Formal Conjectures authors. This PR links an external proof artifact for review under the upstream repository's normal contribution process.
