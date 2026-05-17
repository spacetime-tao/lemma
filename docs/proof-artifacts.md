# Proof Artifacts

A proof artifact is the durable public record of a solved Lemma target.

It exists so a verified proof can be inspected after reward settlement, linked from upstream repositories, and reused by the wider Lean community.

## Artifact Directory

Recommended layout:

```text
proofs/
  <formal-conjectures-commit>/
    <target-id>/
      <claim-id>/
        artifact.json
        target.json
        Submission.lean
        verifier.json
        attestations.json
        README.md
```

This layout is guidance for publication tooling and hosting. It is not a new CLI or protocol contract in this pass.

## Required Files

`artifact.json` is the canonical metadata record. It binds the target, proof, verifier output, attestation, solver identity, and upstream source.

`target.json` contains the registry target row or enough normalized data to reconstruct the exact target.

`Submission.lean` is the accepted proof submission.

`verifier.json` records the verifier result, including toolchain, timeout, policy, stdout/stderr summary, and pass/fail result.

`attestations.json` contains validator or subnet attestation metadata. The exact shape can evolve with the reward mechanism, but it should include enough data for auditors to understand why the proof became eligible.

`README.md` is the human-readable summary with links to source, target, proof, verifier output, and upstream PR status.

## Minimal `artifact.json`

```json
{
  "schema_version": 1,
  "claim_id": "<claim-id>",
  "lemma_target_id": "<target-id>",
  "status": "attested",
  "created_at": "2026-05-17T00:00:00Z",
  "source": {
    "repo": "google-deepmind/formal-conjectures",
    "commit": "<commit>",
    "file": "FormalConjectures/<path>.lean",
    "declaration": "<theorem-name>",
    "original_category": "research open",
    "source_url": "https://github.com/google-deepmind/formal-conjectures/blob/<commit>/<path>"
  },
  "target": {
    "target_sha256": "<target-sha256>",
    "theorem_name": "<theorem-name>",
    "toolchain_id": "leanprover/lean4:<version>",
    "mathlib_rev": "<mathlib-rev>",
    "submission_policy": "restricted_helpers",
    "policy_version": "bounty-policy-v1"
  },
  "proof": {
    "submission_sha256": "<sha256>",
    "artifact_uri": "https://lemmasub.net/proofs/<claim-id>/Submission.lean",
    "license": "Apache-2.0"
  },
  "verification": {
    "passed": true,
    "checked_at": "2026-05-17T00:00:00Z",
    "verifier": "lemma-lean-sandbox",
    "verifier_version": "<version-or-commit>",
    "result_sha256": "<sha256>"
  },
  "attestation": {
    "method": "lemma-subnet",
    "attested_at": "2026-05-17T00:00:00Z",
    "attestation_id": "<id-or-hash>",
    "summary": "<human-readable summary>"
  },
  "solver": {
    "public_id": "<hotkey-or-user-id>",
    "display_name": null
  },
  "upstream": {
    "intended_repo": "google-deepmind/formal-conjectures",
    "status": "pr_prepared",
    "pr_url": null,
    "patch_sha256": "<sha256>"
  }
}
```

## Artifact License

Lean proof code should be published under Apache-2.0 unless the project deliberately chooses another compatible license. The artifact should record the license explicitly.

Miners must understand that submitting a proof for a live Lemma target can permit Lemma to publish the proof artifact and link it in upstream contribution candidates.

## Hashing Rules

Every artifact should include stable hashes:

- target challenge hash,
- submission file hash,
- verifier result hash,
- PR patch hash when generated.

Prefer SHA-256 for public artifact metadata unless protocol code requires another hash.

## Public URL

For the site, reserve this URL shape even before hosting exists:

```text
https://lemmasub.net/proofs/<claim-id>/
```

Do not link this in a live upstream PR until the URL is real and stable.

## Artifact README Template

```md
# Lemma proof artifact: <target-id>

This artifact records a Lean-verified proof accepted by Lemma.

- Target: `<target-id>`
- Source: `<repo>@<commit>:<file>#<declaration>`
- Submission: [`Submission.lean`](Submission.lean)
- Verifier result: [`verifier.json`](verifier.json)
- Attestations: [`attestations.json`](attestations.json)
- Upstream PR: `<url-or-pending>`

Lemma is independent and is not endorsed by Google DeepMind or the Formal Conjectures authors. The proof checks the exact formal target published by Lemma.
```
