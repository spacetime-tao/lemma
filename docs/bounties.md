# Targets And Rewards

This path remains for compatibility with older links. The current concept is targets and rewards.

Lemma rewards proof discovery against published Lean targets. A registry entry is a live reward only when it includes the target payload and confirmed custody metadata.

For the full registry contract, see [target-registry.md](target-registry.md).

For reward flow, see [rewards.md](rewards.md).

## Candidate Targets

Rows without confirmed custody are candidate targets. They may be used for local practice, verification checks, and target review, but they are not live reward offers.

## Live Targets

Live reward-backed targets require:

- `chain_id`
- `contract_address`
- `bounty_id`
- funding confirmation, either `funded: true` or `funding_confirmed_block`

## Claim Flow

1. Fetch a live proof target from the registry.
2. Write `Submission.lean`.
3. Run `lemma mine <target-id> --submission Submission.lean`.
4. Build a custody commit package with `--commit`.
5. Submit the commit transaction to `LemmaBountyEscrow`.
6. Publish the proof artifact and build a reveal package with `--reveal`.
7. Submit the reveal transaction through the custody contract.

The CLI signs an identity-binding message with the configured Bittensor hotkey. That binds the proof artifact, registry hash, claimant address, payout address, and commitment.

## Policy

Live rewards keep proof verification and payout custody separate:

- no manual payout path,
- no unfunded payout claim,
- no subjective proof score,
- no legacy subnet scoring lane.

Lean verification is binary. A proof passes or fails.
