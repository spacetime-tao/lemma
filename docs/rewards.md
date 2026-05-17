# Rewards

Lemma rewards verified proof work according to subnet rules.

Rewards are downstream of verification. A proof must first pass the exact published Lean target and policy.

## Candidate Targets Are Not Reward Offers

Rows without confirmed custody are candidates. They can be listed, inspected, and locally verified, but they are not live reward offers.

Do not describe a target as reward-backed until registry metadata and custody state agree.

## Live Reward Requirements

A live reward target needs:

- target payload,
- registry hash,
- target hash,
- policy version,
- toolchain id,
- custody contract address,
- custody reward id,
- chain id,
- funding confirmation.

## Commit And Reveal Path

For live targets, the CLI can build unsigned transaction data for custody commit and reveal packages.

The commit package binds the target, registry hash, claimant address, payout address, proof artifact hash, hotkey public key, and salt into a commitment.

The reveal package publishes the data needed for custody verification and later resolution.

## Identity Binding

The CLI signs an identity-binding message with the configured Bittensor hotkey. This binds proof artifact metadata, registry hash, claimant address, payout address, and commitment.

## Operator Note

The CLI builds unsigned transaction data. Operators and miners should inspect, sign, and submit transactions with their normal wallet tooling.
