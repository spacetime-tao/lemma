# Validator

Validators poll miners on a fixed interval, verify returned Lean proofs, append
the valid solve set to the solved ledger, and write difficulty-weighted rolling
score weights.

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
- `LEMMA_KNOWN_THEOREMS_MANIFEST_SHA256_EXPECTED`;
- `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED`.

`lemma setup --role validator` prints the expected hashes and asks before
writing suggested `.env` values. Advanced scripts can still use
`lemma validator check`, `lemma validator dry-run`, `lemma validator start`, and
`lemma meta --raw`.

## Polling

`LEMMA_VALIDATOR_POLL_INTERVAL_S` defaults to `300`. The cadence seed is
`floor(chain_head / 100) * 100` by default. Solved-ledger rows do not advance
the next cadence task.

Validators do not poll proof text during commit phase. They poll during reveal
phase, then require a matching commitment at the commit cutoff before running
Lean. UID variants are default-on, so each registered UID receives a
deterministic same-split variant of the anchor theorem.

Verified proofs update rolling scores with difficulty weights. Positive scores
normalize into weights. Same-coldkey partitioning applies work/reward pressure;
it is not Sybil-proof identity.

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
- `LEMMA_UID_VARIANT_PROBLEMS`
- `LEMMA_SCORING_ROLLING_ALPHA`
- `LEMMA_SCORING_COLDKEY_PARTITION`

## Live Task JSON

The validator droplet owns the private solved-target ledger and bounty
acceptance ledger. Publish only stripped JSON from that host:

```bash
uv run lemma dashboard publish --output-dir /var/www/lemma-live
```

Install `deploy/systemd/lemma-live-publisher.service` and
`deploy/systemd/lemma-live-publisher.timer` to refresh
`/var/www/lemma-live/cadence.json` and `/var/www/lemma-live/bounties.json` every
minute. Serve that directory as `live.lemmasub.net` with
`deploy/nginx/lemma-live.conf`. The live JSON files are overwritten in place;
do not publish them through Git commits.
