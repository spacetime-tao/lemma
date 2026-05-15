# Validator

Validators poll miners on a fixed interval, verify returned Lean proofs, append
the valid solve set to the solved ledger, and write miner weights.

## Startup

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma setup --role validator
uv run lemma validate
```

Validators require:

- Docker verification enabled with `LEMMA_USE_DOCKER=true`;
- `LEMMA_TARGET_GENESIS_BLOCK` before the first target can run;
- `LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED`;
- `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED`.

`lemma setup --role validator` prints the expected hashes and asks before
writing suggested `.env` values. Advanced scripts can still use
`lemma validator check`, `lemma validator dry-run`, `lemma validator start`, and
`lemma meta --raw`.

## Polling

`LEMMA_VALIDATOR_POLL_INTERVAL_S` defaults to `300`. The active target is not
chosen by block seed. It is always the first manifest target not already present
in the solved ledger.

Validators do not poll proof text during commit phase. They poll during reveal
phase, then require a matching commitment at the commit cutoff before running
Lean. The earliest valid commitment block wins; same-block valid commitments
split. If no proof verifies and there is no previous solver set, the validator
skips `set_weights`.

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
