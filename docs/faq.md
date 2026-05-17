# FAQ

## What Is Lemma?

Lemma is a Bittensor subnet for Lean-verified proof discovery. It publishes formal targets, miners submit Lean proof files, validators check them, and verified proofs become eligible for rewards.

## What Is Lean?

Lean is an interactive theorem prover. It checks whether formal mathematical statements and proofs are valid under a precise logical environment.

## What Is Formal Conjectures?

Formal Conjectures is a public Lean 4 and mathlib repository containing formalized conjectures and related mathematical statements. Lemma uses public Formal Conjectures statements as target material.

## Is Lemma Endorsed By Google DeepMind?

No. Lemma is independent. It uses public statements from `google-deepmind/formal-conjectures` as source material, but it is not endorsed by Google DeepMind or the Formal Conjectures authors.

## What Do Miners Submit?

Miners submit a `Submission.lean` proof file for the exact published target.

## Can Miners Use AI?

Yes. Lemma does not require a specific proof-search method. Models, tactics, retrieval systems, and human-written proofs are all acceptable if the submitted proof passes the verifier.

## What Do Validators Do?

Validators fetch the target registry, run the pinned Lean verifier, and use the verification result as the correctness signal.

## What Is A Proof Artifact?

A proof artifact is the public record of a solved Lemma target. It should bind the source target, accepted `Submission.lean`, verifier result, hashes, attestation metadata, and upstream PR status when applicable.

## Does Lemma Open Upstream PRs?

Lemma can prepare upstream PR candidates for solved Formal Conjectures targets. The intended PR marks the target solved and links to the public proof artifact through the upstream `formal_proof` mechanism.

This is a publication path, not upstream acceptance by default. Upstream maintainers retain normal review authority.

## Does Verification Prove The Original Informal Conjecture?

Lean verification proves the published formal target. It does not by itself guarantee that an upstream informal conjecture was perfectly formalized.

## What Is A Candidate Target?

A candidate target is verifier-ready but does not have confirmed reward custody. It is useful for practice, testing, and review.

## What Is A Live Target?

A live target has confirmed custody metadata and can produce reward custody transaction data after a proof verifies locally.

## Are Rewards Guaranteed?

No. Verified proofs become eligible for rewards under subnet and custody rules. Public docs should not promise rewards.

## Does Upstream Merge Control Rewards?

No. Reward eligibility depends on the published target, verifier result, attestation, and active subnet rules. Upstream PR acceptance is independent review after Lemma has verified the target.
