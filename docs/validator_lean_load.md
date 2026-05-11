# Validator Lean Load

Validator CPU work comes mostly from Lean verification.

Tune two things separately:

- concurrency: how many Lean jobs run at once;
- attest spot verify: how often an attested proof still gets full Docker Lean.

## Concurrency

| Env | Role |
| --- | --- |
| `LEMMA_LEAN_VERIFY_MAX_CONCURRENT` | Max Lean verify jobs per epoch. Lower it if RAM, CPU, or Docker stalls. |
| `LEMMA_LEAN_VERIFY_REMOTE_URL` | Optional remote Lean worker URL. |

Epoch logs include the caps in use.

## Warm Caches

The first proof for a generated template can be slow. Lemma may need to create a
Lake workspace, populate `.lake`, and write a cache slot.

Later proofs for the same template can reuse the warm workspace.

Best practice:

1. Build the sandbox image before running a validator:
   `bash scripts/prebuild_lean_image.sh`.
2. Put `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` on fast persistent disk.
3. Use `LEMMA_LEAN_DOCKER_WORKER` for a long-lived Docker worker.
4. Leave `LEMMA_LEAN_ALWAYS_CACHE_GET` unset unless refreshing caches on purpose.
5. Leave `LEMMA_LEAN_PROOF_METRICS` off for production-speed validation.
6. Measure with `LEMMA_LEAN_VERIFY_TIMING=1` on production-like hardware.

Cold-cache timing is not the steady-state budget, but it matters after releases,
new templates, new images, or new cache directories.

## 2026-05 Testnet Note

A 4 vCPU / 8 GB shared Linux worker with a long-lived Docker worker saw:

- about 292 seconds cold;
- about 25 seconds warm.

That supports shorter windows only for small loads. Larger miner counts need
more concurrency, dedup, attest policy, or a worker pool.

## Reuse Inside One Batch

Lemma reduces duplicate work in two ways:

- one cold template warmup can unblock waiting proofs for that template;
- identical proof payloads can reuse one Lean result.

This helps with same-model clones. It does not replace real verifier capacity
for many different proofs.

## Miner Verify Attest

Requires:

```text
LEMMA_MINER_VERIFY_ATTEST_ENABLED=1
```

Miners must run local Lean PASS and sign
[`miner_verify_attest_message`](../lemma/protocol_attest.py).

`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION` controls how often validators
still run full Docker Lean:

| Value | Behavior |
| --- | --- |
| `1.0` | Always full verify. Safest. Highest CPU. |
| `(0, 1)` | Full verify a deterministic subset. Trust attest for the rest. |
| `0.0` | Never full verify. High trust. High risk. |

Keep `1.0` until miners reliably run local verify and signatures validate.

If lowering the fraction, set `LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT` and
watch full-verify failures.

## Cadence

Shorter generated windows are policy choices, not free defaults.

Measure these before shortening windows:

- warm-cache Lean time;
- remote worker throughput;
- miner response latency;
- validator weight-setting cadence.

Remember:

- `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` controls theorem rotation.
- Validator service cadence follows subnet epoch boundaries.

Reducing theorem windows does not by itself make validators write weights more
often.

## Offload Lean

Set `LEMMA_LEAN_VERIFY_REMOTE_URL` to send proofs to `lemma lean-worker`.

Then network and worker capacity become the limit. Align
`LEMMA_LEAN_VERIFY_REMOTE_BEARER` and timeouts with production.

## References

- [`LemmaSettings`](../lemma/common/config.py)
- [miner-verify-attest.md](miner-verify-attest.md)
- [incentive_migration.md](incentive_migration.md)
