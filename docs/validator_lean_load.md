# Validator Lean load and attest spot-verify

Operators tuning CPU on validators should separate **concurrency caps** (how many jobs run at once) from **spot full-verify fraction** (what fraction of attest-eligible responses still run Docker Lean).

Subnet design context: [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) (`compute_distribution` — push heavy work to miners where possible).

## Concurrency caps

| Env | Role |
| --- | --- |
| **`LEMMA_LEAN_VERIFY_MAX_CONCURRENT`** | Max concurrent Lean verify jobs per epoch (each may use Docker). Raises throughput when many miners return proofs; lower if RAM/CPU or Docker stalls. |
| **`LEMMA_JUDGE_MAX_CONCURRENT`** | Max concurrent judge HTTP calls after Lean passes. Tune against provider rate limits (e.g. Chutes). |

Epoch logs include the caps in use (see `lemma_epoch_summary` / debug lines in [`epoch.py`](../lemma/validator/epoch.py)).

## Miner verify attest + spot full-verify

Requires **`LEMMA_MINER_VERIFY_ATTEST_ENABLED=1`**. Miners must run local Lean PASS and sign [`miner_verify_attest_message`](../lemma/protocol_attest.py); validators verify Sr25519 against the metagraph hotkey.

**`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** (default **`1.0`**) controls how often the validator still runs **full Docker Lean verify** vs trusting the attest for scoring that round:

| Value | Behavior |
| --- | --- |
| **`1.0`** | Always full verify when attest is enabled (safest; highest CPU). |
| **`(0, 1)`** | Deterministic subset: [`attest_spot_should_full_verify`](../lemma/protocol_attest.py) hashes `(salt, uid, theorem_id, metronome_id)` — roughly **fraction ×** tuples get full verify; the rest skip Lean with **`VerifyResult(passed=True, reason="attest_trusted")`** (still scored downstream, but neutral for verify-credibility updates). |
| **`0.0`** | Never full verify — **trust attest only**. Dangerous unless you fully accept cheating risk. |

**Operational order:** keep **`1.0`** until miners reliably run **`LEMMA_MINER_LOCAL_VERIFY=1`** and attest signatures validate; then set a non-empty **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT`**, lower gradually (e.g. **0.5**, **0.25**), and monitor full-verify failures and miner fraud reports. `lemma meta` pins only the salt SHA-256, not the salt text.

Attest **disabled**: spot fraction is ignored (full verify path uses normal Lean unless other shortcuts apply).

## Offload Lean to another host

**`LEMMA_LEAN_VERIFY_REMOTE_URL`** POSTs proofs to **`lemma lean-worker`** — validator CPU drops; network + worker capacity become the limit ([`verify_runner.py`](../lemma/lean/verify_runner.py)). Align **`LEMMA_LEAN_VERIFY_REMOTE_BEARER`** and timeouts with production.

## References

- Config fields: [`LemmaSettings`](../lemma/common/config.py) (`lemma_miner_verify_attest_*`, `lemma_lean_verify_max_concurrent`, …).
- Incentive overview: [incentive_migration.md](incentive_migration.md).
