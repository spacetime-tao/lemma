# Bounties And Escrow

Lemma rewards proof formalization only through funded escrow. A registry entry is a live bounty when it includes escrow metadata with:

- `chain_id`
- `contract_address`
- `bounty_id`
- funding confirmation, either `funded: true` or `funding_confirmed_block`

Rows without funded escrow are candidates. They may be useful for local practice or preflight, but they are not reward offers.

## Registry

The bounty registry is JSON. Each row contains a Lean problem payload, source metadata, submission policy, toolchain id, policy version, and optional escrow metadata. The CLI checks the registry hash when `LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED` is set.

The target hash is derived from the Lean challenge source. If a row supplies `target_sha256`, it must match the derived value.

## Claim Flow

1. Fetch a funded bounty from the registry.
2. Write `Submission.lean`.
3. Run `lemma mine <bounty-id> --submission Submission.lean`.
4. Build a commit package with `--commit`.
5. Submit the commit transaction to `LemmaBountyEscrow`.
6. Publish the proof artifact and build a reveal package with `--reveal`.
7. Submit the reveal transaction to escrow.

The CLI signs an identity-binding message with the configured Bittensor hotkey. That binds the proof artifact, registry hash, claimant address, payout address, and escrow commitment.

## Policy

Live bounties are trustless-only:

- no manual payout path
- no unfunded reward promise
- no subjective proof score
- no legacy subnet scoring lane

Lean verification is binary. A proof passes or fails.
