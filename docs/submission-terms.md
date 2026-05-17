# Submission And Publication Terms

This page describes the publication expectations for Lemma proof submissions.

It is not legal advice. It is an operator-facing statement of how Lemma treats proof artifacts.

## Publication Permission

Live target terms should make clear that by submitting a proof artifact for that target, the submitter permits Lemma to:

- verify the submitted proof,
- publish the proof artifact after verification and attestation,
- store and mirror the proof artifact in Lemma-controlled public locations,
- link the proof artifact from upstream contribution candidates,
- include target, proof, verifier, and attestation metadata in public records,
- attribute the proof to the submitter's chosen public identity or protocol identity.

## Recommended License

Proof code should be published under Apache-2.0 unless a different compatible license is explicitly selected.

The artifact metadata should record the chosen license.

## Solver Attribution

A solver can be identified by protocol identity, public handle, or both. Docs and artifact schemas should avoid requiring doxxing. A Bittensor hotkey or other public protocol identifier is sufficient for protocol attribution.

## Upstream Contributions

If the proof corresponds to a Formal Conjectures target, Lemma may prepare an upstream PR candidate linking to the public proof artifact.

Upstream maintainers retain normal review authority. Lemma cannot guarantee that an upstream PR will be accepted.

## Formal Target Caveat

Lean verification proves the exact formal target. It does not guarantee that the informal source conjecture was perfectly captured by the formal statement.

## Sensitive Data

Do not include private credentials, local paths, wallet data, private deployment notes, or private operator state in proof artifacts.
