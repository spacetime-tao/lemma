# Validator

Validators poll miners on a fixed interval, verify returned Lean proofs, append
the first valid solve to the WTA ledger, and write champion-only weights.

## Startup

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma meta --raw
uv run lemma validator check
uv run lemma validator start
```

Validators require:

- Docker verification enabled with `LEMMA_USE_DOCKER=true`;
- `LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED`;
- `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED`.

Copy the two expected hashes from `lemma meta --raw` into `.env`.

## Polling

`LEMMA_VALIDATOR_POLL_INTERVAL_S` defaults to `300`. The active target is not
chosen by block seed. It is always the first manifest target not already present
in the solved ledger.

If multiple proofs verify in one poll, the lowest UID wins deterministically. If
no proof verifies and there is no previous champion, the validator skips
`set_weights`.

## Lean Verify

Validators build the `Solution` bridge target so the submitted theorem must
match the locked statement. `sorry`, `admit`, new axioms, unsafe code, timeouts,
and mismatched target fields cannot win.

Useful knobs:

- `LEAN_SANDBOX_IMAGE`
- `LEAN_VERIFY_TIMEOUT_S`
- `LEMMA_LEAN_VERIFY_MAX_CONCURRENT`
- `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`
- `LEMMA_VALIDATOR_MIN_FREE_BYTES`
