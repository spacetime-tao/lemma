# Bounties

Lemma bounties are not live yet.

Bounties are planned manual reviewed rewards for harder Lean proof work. They
are separate from timed cadence rounds: no timer, no automatic validator
scoring, and no current payout or claim intake.

## Intended Flow

1. Lemma publishes a bounty record before the proof is public.
2. The solver works through a public GitHub process: Formal Conjectures PR,
   issue, maintainer-recognized proof link, or external proof repository.
3. The solver includes a structured Lemma bounty claim.
4. Lemma verifies the pinned target, proof artifact, environment, and claimant.
5. A reviewer makes the payout decision manually.

For high-value bounties, final payout should require a review or challenge
period plus upstream acceptance or a recognized `formal_proof` link.

## Bounty Record

Every live bounty should record:

- `bounty_id`
- theorem name
- source URL
- Formal Conjectures commit or tag
- Lean version
- Mathlib version
- target statement hash
- reward amount
- creation timestamp
- whether Formal Conjectures `formal_proof` existed at creation time

Normal proof bounties must exclude targets that already had `formal_proof` at
creation time. Those targets can only be explicit proof-porting or
simplification work.

## Claim Record

A TAO address comment in Lean code is not enough. It may be included as extra
metadata, but the source of truth should be a structured claim in a GitHub PR,
issue, proof repository, or Lemma bounty registry record.

```text
Lemma bounty claim
Bounty ID: lemma-bounty-0007
Theorem: AgohGiuga.isWeakGiuga_iff_prime_dvd
Claimant GitHub: @username
Claimant TAO address: 5...
Formal Conjectures commit/PR: ...
Proof commit: ...
Wallet signature: optional for small bounties, required for high-value bounties
```

The preferred high-value claim binds the GitHub identity, proof commit, bounty
ID, theorem name, and TAO address in a wallet-signed message.

## Statuses

Future claim statuses:

- `open`
- `submitted`
- `lemma_verified`
- `upstream_review`
- `accepted_formal_proof`
- `paid`
- `rejected`
- `disputed`

## Verification Policy

Lemma bounties are allowlisted. The registry owns the imports, theorem name,
theorem statement, Lean toolchain, Mathlib revision, target hash, and submission
policy.

The default bounty policy is `restricted_helpers`:

- imports must match the registry exactly;
- code must live inside `namespace Submission`;
- helper `def`, `lemma`, and `theorem` declarations are allowed;
- the final theorem must match the exact target theorem and type;
- `sorry`, `admit`, new `axiom` or `constant` declarations, unsafe/native/debug
  hooks, custom syntax/macros/elaborators, notation, attributes, extra imports,
  and target edits are rejected.

The final theorem and helper theorem/lemma declarations are also checked for
axiom dependencies. Only the approved Lean/Mathlib baseline is accepted.

## Current Repo State

The checked-in bounty registry may contain draft targets for local verification
and client development. Draft targets are not payout offers.

Useful local commands while the lane is still draft-only:

```bash
uv run lemma bounty list --all
uv run lemma bounty show <bounty-id>
uv run lemma bounty verify <bounty-id> --submission Submission.lean
uv run lemma bounty package <bounty-id> --submission Submission.lean --payout <SS58>
```

`lemma bounty submit` is an experimental client path for a future bounty API. Do
not treat it as live claim intake unless a specific bounty page says claims are
open and names the review process.
