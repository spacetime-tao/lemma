# Validator

Validators poll miners on a fixed interval, verify returned Lean proofs, append
the valid solve set to the solved ledger, and write current-epoch miner plus
owner/burn weights.

## Startup

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma setup --role validator
uv run lemma validate
```

Use `--wallet` and `--hotkey` when the validator should sign with a different
registered hotkey than the miner:

```bash
uv run lemma setup --role validator --hotkey lemmaminer2
uv run lemma validate --hotkey lemmaminer2
```

Validators require:

- Docker verification enabled with `LEMMA_USE_DOCKER=true`;
- `LEMMA_TARGET_GENESIS_BLOCK` before the first target can run;
- `LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED`;
- `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED`;
- `LEMMA_OWNER_BURN_UID` for the unearned epoch budget.

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
split. Unearned weight always routes to `LEMMA_OWNER_BURN_UID`; previous solver
sets do not keep getting paid for failed later epochs.

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
- `LEMMA_OWNER_BURN_UID`
