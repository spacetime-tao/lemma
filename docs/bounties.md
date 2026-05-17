# Proof Targets And Rewards

Lemma rewards proof formalization against published Lean targets. A registry entry is a live reward when it includes the target payload and confirmed custody metadata with:

- `chain_id`
- `contract_address`
- `bounty_id`
- funding confirmation, either `funded: true` or `funding_confirmed_block`

Rows without confirmed custody are candidate targets. They may be useful for local practice or preflight, but they are not live reward offers.

## Registry

The target registry is JSON. Each row contains a Lean problem payload, source metadata, submission policy, toolchain id, policy version, and optional custody metadata. The CLI checks the registry hash when `LEMMA_BOUNTY_REGISTRY_SHA256_EXPECTED` is set.

The target hash is derived from the Lean challenge source. If a row supplies `target_sha256`, it must match the derived value.

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

- no manual payout path
- no unfunded payout claim
- no subjective proof score
- no legacy subnet scoring lane

Lean verification is binary. A proof passes or fails.
