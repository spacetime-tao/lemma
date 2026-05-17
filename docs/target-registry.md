# Target Registry

The target registry is the source of truth for Lemma work.

The current JSON shape uses a top-level `bounties` list for historical compatibility. Public docs can call those rows targets, but code still reads the `bounties` field.

## Candidate Targets And Live Targets

A candidate target has a verifier-ready problem payload but no confirmed reward custody. It can be listed, inspected, and locally verified. It is not a reward offer.

A live target has confirmed custody metadata and matching custody state. Only live targets can produce commit or reveal transaction packages.

## Required Target Fields

Every row should include:

- `id`
- `kind`
- `status`
- `title`
- `problem`
- `source`
- `submission_policy`
- `policy_version`
- `toolchain_id`
- `target_sha256`

Rows may include `reward`, `deadline`, `terms_url`, and `escrow`.

## Problem Payload

The `problem` object defines the Lean statement:

```json
{
  "id": "fc.example.target",
  "theorem_name": "target_theorem",
  "type_expr": "True",
  "split": "bounty",
  "lean_toolchain": "leanprover/lean4:v4.30.0-rc2",
  "mathlib_rev": "<mathlib-rev>",
  "imports": ["Mathlib"],
  "extra": {
    "informal_statement": "Plain-language context."
  }
}
```

## Target Hash

`target_sha256` is derived from the Lean challenge source. If a registry row supplies a target hash, the CLI recomputes it and rejects mismatches.

## Toolchain Pinning

Every target must pin the Lean and mathlib environment. Validators should not guess. If the target came from Formal Conjectures, include the upstream commit and file in `source.formal_conjectures`.

## Submission Policy

`submission_policy` tells the verifier how to scan `Submission.lean` before Lean runs. The current public target flow uses `restricted_helpers`.

## Source Metadata

For Formal Conjectures targets, include:

- upstream repository,
- commit,
- file,
- declaration,
- category when known,
- formal proof metadata when present.

If formal proof metadata is present, set `kind` to `proof_porting`.

## Artifact And Upstream Metadata

Registry rows should contain enough public source metadata to support proof artifact publication later. For Formal Conjectures targets, preserve the upstream repository, commit, file, declaration, category, and existing `formal_proof` metadata.

Do not add fake artifact URLs or fake upstream PR URLs to a target row. Artifact and PR metadata should be published only after a proof verifies, attestation is complete, and a real artifact or PR package exists.

Use `terms_url` to point miners at submission and publication terms when a live target may publish accepted proofs.

## Status Values

Use the values currently supported by code and operators:

- `candidate`
- `active`
- `open`
- `solved`
- `closed`

Use `candidate` for examples without confirmed custody.

## Example Candidate

```json
{
  "id": "fc.<short-source>.<declaration>",
  "kind": "formal_target",
  "status": "candidate",
  "reward": "Reward pending",
  "source": {
    "name": "Formal Conjectures",
    "url": "https://github.com/google-deepmind/formal-conjectures/blob/<commit>/<path>",
    "formal_conjectures": {
      "repo": "google-deepmind/formal-conjectures",
      "commit": "<commit>",
      "file": "<path>",
      "declaration": "<name>",
      "category": "research open",
      "has_formal_proof": false,
      "formal_proof_url": ""
    }
  }
}
```
