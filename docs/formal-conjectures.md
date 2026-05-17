# Formal Conjectures As Lemma's Target Supply

Formal Conjectures is a public Lean 4 and mathlib project containing formalized conjectures and related mathematical statements. Lemma uses those public statements as source material for proof targets.

## Relationship To Formal Conjectures

Lemma is independent infrastructure. It is not endorsed by Google DeepMind or the Formal Conjectures authors.

The intended relationship is narrow:

1. Formal Conjectures provides public Lean statements.
2. Lemma selects suitable statements.
3. Lemma pins the exact upstream commit, file, declaration, and toolchain.
4. Miners search for proofs against the pinned target.
5. Validators check submitted proofs with Lemma's verifier path.

## Why This Source Matters

Synthetic examples are useful for testing, but public formal statements make the target supply more meaningful. Formal Conjectures gives Lemma a source of real mathematical formalization work with explicit Lean declarations and upstream provenance.

## Target Selection Criteria

A good Lemma target should be:

- expressible as one exact Lean theorem statement,
- reproducible from pinned source metadata,
- compatible with the verifier image and submission policy,
- small enough for miners to inspect,
- clear about whether it is proof discovery or proof porting,
- free of fake reward claims until custody is confirmed.

## Open Target Vs Proof-Porting Target

Formal Conjectures may contain metadata pointing to known formal proofs.

A proof-discovery target asks miners to find a proof for a statement that is not already published as a formal proof in the source metadata.

A proof-porting target asks miners to adapt or package a known formal proof into Lemma's verifier boundary.

The code enforces this guardrail: if a Formal Conjectures source has `formal_proof`, `has_formal_proof`, or `formal_proof_url` metadata, the registry row must use `kind=proof_porting`.

## Recommended Source Metadata

```json
{
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
```

## Fidelity Caveat

Lean verification checks the published formal target. It does not guarantee that an upstream informal conjecture was perfectly formalized. Public copy should keep that distinction clear.

## Contribution Loop

When a Lemma proof is useful upstream, preserve exact target IDs, source commits, proof artifact hashes, and links to the Lean file so humans can review whether it should become part of a public formalization repository.
