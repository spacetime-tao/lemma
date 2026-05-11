# Validator Lean load and attest spot-verify

Operators tuning CPU on validators should separate **concurrency caps** (how many jobs run at once) from **spot full-verify fraction** (what fraction of attest-eligible responses still run Docker Lean).

Subnet design context: [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) (`compute_distribution` — push heavy work to miners where possible).

## Concurrency caps

| Env | Role |
| --- | --- |
| **`LEMMA_LEAN_VERIFY_MAX_CONCURRENT`** | Max concurrent Lean verify jobs per epoch (each may use Docker). Raises throughput when many miners return proofs; lower if RAM/CPU or Docker stalls. |
| **`LEMMA_LEAN_VERIFY_REMOTE_URL`** | Optional remote Lean worker URL; moves verifier CPU off the validator host when operators need more throughput. |

Epoch logs include the caps in use (see `lemma_epoch_summary` / debug lines in [`epoch.py`](../lemma/validator/epoch.py)).

## Warm-cache verification

The first verification for a generated theorem template can be much slower than
later attempts. On a cold template slot, Lemma may need to materialize the Lake
workspace, populate `.lake`, and publish the workspace into
`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`. Once that slot is warm, later proofs for
the same template reuse the workspace and usually skip `lake exe cache get`.

Can validators skip warmups entirely? Not literally. Lean still has to load the
pinned toolchain, use Mathlib artifacts, elaborate the submitted `Submission.lean`,
and check the proof. The goal is to move one-time work out of the hot path:
prebuild the sandbox image, keep `.lake` on persistent disk, and reuse a
long-lived worker so normal rounds pay mostly for the submitted proof, not for
fresh setup.

Best current practice:

1. Build the sandbox image before running a validator:
   `bash scripts/prebuild_lean_image.sh`.
2. Keep a persistent workspace cache directory on fast local disk
   (`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`).
3. Run a long-lived Docker worker with `LEMMA_LEAN_DOCKER_WORKER` so verification
   uses `docker exec` instead of creating a fresh container every proof.
4. Leave `LEMMA_LEAN_ALWAYS_CACHE_GET` unset in normal operation; set it only when
   you intentionally want to refresh Lake caches.
5. Leave `LEMMA_LEAN_PROOF_METRICS` off for production-speed validation; enable
   it only for calibration/export runs where the extra Lean probe is worth the
   latency.
6. Measure with `LEMMA_LEAN_VERIFY_TIMING=1` on production-like hardware before
   shortening theorem windows.

Cold-cache measurements should not be used as the steady-state validator budget,
but they matter operationally: after a release, a new template, a new image, or a
new cache directory, the first passing proof can pay the warmup cost.

**2026-05 testnet note:** a 4 vCPU / 8 GB shared Linux worker using a
long-lived Docker worker and persistent workspace cache verified a simple
generated proof in about **292 s cold** (Mathlib cache download/decompress) and
about **25 s warm** on repeated runs. That is compatible with shorter theorem
windows for small miner counts, but hundreds of miners require concurrency,
dedup, attest/spot policy, and likely a worker pool rather than one small box.
On the same host, baking the full Mathlib cache into one huge Docker layer was
brittle; the lighter Lean image plus persistent cache was the reliable path.

When several proofs for the same cold template arrive together, the validator now
uses a per-template singleflight: one proof pays the cold warmup and publishes the
warm slot; the waiting proofs then reuse that slot. This reduces duplicate
startup work inside one validator process. It does not remove the need for more
Lean capacity when many distinct templates or genuinely different cold slots are
being checked.

Validators also reuse Lean verification results for identical proof payloads in
one batch. If several miners submit the same theorem/proof script, the validator
checks that Lean payload once and applies the verification result to each
matching miner response before scoring. This helps with
same-model clones and early testnet data collection, but it is not a substitute
for more verifier capacity when many miners submit genuinely different proofs.

## Miner verify attest + spot full-verify

Requires **`LEMMA_MINER_VERIFY_ATTEST_ENABLED=1`**. Miners must run local Lean PASS and sign [`miner_verify_attest_message`](../lemma/protocol_attest.py), which binds the validator hotkey; validators verify Sr25519 against the metagraph hotkey. Threat model: [miner-verify-attest.md](miner-verify-attest.md).

**`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** (default **`1.0`**) controls how often the validator still runs **full Docker Lean verify** vs trusting the attest for scoring that round:

| Value | Behavior |
| --- | --- |
| **`1.0`** | Always full verify when attest is enabled (safest; highest CPU). |
| **`(0, 1)`** | Deterministic subset: [`attest_spot_should_full_verify`](../lemma/protocol_attest.py) hashes `(salt, uid, theorem_id, metronome_id)` — roughly **fraction ×** tuples get full verify; the rest skip Lean with **`VerifyResult(passed=True, reason="attest_trusted")`** (still scored downstream, but neutral for verify-credibility updates). |
| **`0.0`** | Never full verify — **trust attest only**. Dangerous unless you fully accept cheating risk. |

**Operational order:** keep **`1.0`** until miners reliably run **`LEMMA_MINER_LOCAL_VERIFY=1`** and attest signatures validate; then set a non-empty **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT`**, lower gradually (e.g. **0.5**, **0.25**), and monitor full-verify failures and miner fraud reports. `lemma meta` pins only the salt SHA-256, not the salt text.

Attest **disabled**: spot fraction is ignored (full verify path uses normal Lean unless other shortcuts apply).

## Cadence Implications

Shorter generated windows, such as 25 blocks (~5 minutes at the 12 s estimate)
or 50 blocks (~10 minutes), are possible policy choices, not free defaults.
They should be adopted only after operators measure warm-cache verification,
remote worker throughput, and miner response latency on production-like Linux hosts.

Also distinguish two clocks:

- `LEMMA_PROBLEM_SEED_QUANTIZE_BLOCKS` controls how often the shared generated
  theorem changes.
- The bundled validator service waits for subnet epoch boundaries before running
  live rounds and `set_weights`.

Reducing theorem windows from 100 blocks to 50 or 25 blocks increases theorem
variety and shortens miner response budgets, but it does not by itself make the
validator write weights more often. For 5- or 10-minute scored rounds, the full
validator cadence, weight-setting policy, forward wait,
proof-scoring cost, and warm-cache Lean timing need to be reviewed together.

Miner verify attest can reduce validator Lean load, but only after miners run
`LEMMA_MINER_LOCAL_VERIFY=1`, attest signatures validate, and validators keep a
nonzero spot full-verify fraction. Until that evidence exists, keep the default
mental model simple: validators fully verify passing candidate proofs.

## Offload Lean to another host

**`LEMMA_LEAN_VERIFY_REMOTE_URL`** POSTs proofs to **`lemma lean-worker`** — validator CPU drops; network + worker capacity become the limit ([`verify_runner.py`](../lemma/lean/verify_runner.py)). Non-loopback workers require **`LEMMA_LEAN_VERIFY_REMOTE_BEARER`** unless **`LEMMA_LEAN_WORKER_ALLOW_UNAUTHENTICATED_NON_LOOPBACK=1`** is set for dev-only exposure. Align bearer auth and timeouts with production.

## References

- Config fields: [`LemmaSettings`](../lemma/common/config.py) (`lemma_miner_verify_attest_*`, `lemma_lean_verify_max_concurrent`, …).
- Incentive overview: [incentive_migration.md](incentive_migration.md).
