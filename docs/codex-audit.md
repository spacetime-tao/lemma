# Lemma codebase audit (Codex assessment)

This document records an engineering and security posture review of the Lemma
repository ([github.com/spacetime-tao/lemma](https://github.com/spacetime-tao/lemma)),
refreshed after the local hardening pass on 2026-05-13. It is not a penetration
test, formal verification of the Python stack, or an independent third-party
security audit.

The review lens remains strict: **treat every line of code as a liability**. A
line should justify itself by reducing risk, clarifying the system, or making
invalid states harder to express.

---

## Rating

**8.4 / 10** - **A- local engineering quality** for an early-stage Bittensor
testnet subnet. For adversarial production readiness alone, the rating is
**B / B-** because Docker, Bittensor economics, live ops, and external-audit
coverage remain outside what this repository can prove by itself.

| Dimension | Score (0-10) | Comment |
| --- | ---: | --- |
| Architecture and clarity | 8.4 | The protocol/miner/validator/Lean/scoring split is clear, and the latest pass tightened the validator hot path without adding a parallel framework. |
| Proof-only mechanism fit | 8.6 | The live eligibility rule is still binary Lean proof verification. Verifier-local failures are now separated from proof failures, reducing accidental punishment from local infra breakage. |
| Testing and CI | 8.7 | Focused hardening tests were added for export failure, disk preflight, cache byte pruning, infra accounting, RPC backoff, dashboard locking, and retired legacy aliases. Local non-Docker gates pass. |
| Security posture | 8.1 | Remote worker exposure, oversized payloads, export side effects, disk pressure, and stale legacy profile aliases now have tighter defaults or cleaner failure modes. |
| Line liability / simplicity | 8.0 | Runtime `assert`s and silent cleanup exceptions were removed where they obscured behavior. Remaining Bandit lows are intentional subprocess/RNG surfaces rather than broad hidden exception paths. |

This should be read as progress toward 10, not arrival at 10. A true 10 would
need GitHub Actions evidence for each saved head, live testnet evidence,
external infra review, and continued deletion/isolation of research-only
surfaces. The broader audit head `2b0c076` passed GitHub Actions; the
set_weights follow-up still needs its own push and CI confirmation.

---

## Closed since the 7.2 audit

1. **Validator response size cap is symmetric.**

   The shared synapse limit rejects oversized `resp.proof_script` payloads in
   the validator epoch path before verification work is queued.

2. **Remote Lean worker defaults are safer.**

   Non-loopback `lemma lean-worker` binds require bearer auth unless the
   explicit dev-only unauthenticated override is set.

3. **Export writes no longer block grading.**

   Training/dashboard JSONL appends are non-consensus side effects. If an
   `OSError` occurs after scoring, the validator logs the failure and continues
   toward `set_weights` with the already-computed scores.

4. **Disk pressure is checked before miner queries.**

   `LEMMA_VALIDATOR_MIN_FREE_BYTES` now gates root/cache free space before an
   epoch opens Dendrite or queries miners. Low disk becomes a validator infra
   skip, not a partial miner failure pattern.

5. **Lean workspace cache has a byte cap.**

   `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES` complements
   `LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS`, pruning old warm slots by total size
   while protecting the active slot.

6. **Verifier-local failures are accounted separately.**

   `timeout`, `oom`, `docker_error`, and `remote_error` are counted as validator
   infra failures in epoch summaries and exported round summaries via
   `verify_infra_error_uids`. They do not lower verify credibility as if they
   were ordinary miner proof failures.

7. **All-fail proof epochs persist credibility updates.**

   Ordinary Lean proof failures now save verify-credibility downgrades even when
   no miner scored in that epoch. Verifier-local infra failures remain excluded.

8. **Validator loop handles RPC rate pressure better.**

   Chain/RPC errors around cadence calculation no longer fall out of the
   service loop. HTTP 429/rate-limit style errors use a longer backoff.

9. **Set-weights failures are less ambiguous.**

   Tuple-style false returns and raised RPC exceptions from `set_weights` are
   treated as failures, retried, and logged with a concrete final message.

10. **Dashboard refresh is serialized.**

   `deploy/scripts/lemma-refresh-public-dashboard` now uses `flock`, cleans its
   temp file on exit, and remains isolated from validator scoring.

11. **Legacy live-adjacent aliases were retired.**

   `reasoning_only`, `LEMMA_JUDGE_PROFILE_ATTEST_*`,
   `JUDGE_PROFILE_SHA256_EXPECTED`, `/lemma/judge_profile_sha256`, and JSON
   `judge_profile_sha256` peer attest compatibility are no longer accepted live
   surfaces. The supported public naming is validator-profile oriented.

12. **Low-severity Bandit noise was reduced where it clarified code.**

    Runtime `assert` statements and silent broad cleanup exceptions were removed.
    Full Bandit lows dropped from 27 to 20.

---

## Remaining gaps

1. **GitHub Actions evidence for the set_weights follow-up is still needed.**

   Local gates pass, and the broader audit head `2b0c076` passed GitHub
   Actions. The small set_weights result-handling follow-up still needs push and
   CI confirmation.

2. **Full Bandit still reports 20 low-severity findings.**

   The remaining lows are intentional subprocess use in Lean/Docker verifier
   paths and deterministic non-crypto RNG/jitter. Do not add wrappers merely to
   silence them; reduce them only when it removes code or ambiguity.

3. **Live ops evidence is still needed.**

   Local proof PASS is not enough. The subnet still needs measured miner
   response time, prover latency, validator verify time, scored miner count,
   timeout/fail reasons, `set_weights` behavior, and emission movement from
   live testnet runs.

4. **External review is still absent.**

   Before high-value mainnet operation, budget an independent review focused on
   validator infra, Docker/worker exposure, Bittensor operations, and key
   custody.

---

## Verification run

Verified against the local working tree based on `9546095`:

| Check | Result |
| --- | --- |
| `.venv/bin/ruff check lemma tests tools` | Passed. |
| `.venv/bin/mypy lemma` | Passed: `Success: no issues found in 70 source files`. |
| `.venv/bin/pytest tests -q` | Passed: `310 passed, 2 skipped, 12 warnings`. |
| `.venv/bin/python scripts/ci_verify_generated_templates.py` | Passed metadata/witness gate: `OK: generated template metadata/witness gate covered 80 builders`. |
| `RUN_DOCKER_LEAN=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/pytest tests/test_docker_golden.py -v --tb=short` | Passed: `1 passed in 208.57s`. |
| `RUN_DOCKER_LEAN_TEMPLATES=1 LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest .venv/bin/python scripts/ci_verify_generated_templates.py` | Passed: all 80 generated template stubs and witnesses built in one Docker workspace. |
| `docker build -f Dockerfile -t lemma-runtime:ci-smoke .` | Passed. |
| `.venv/bin/bandit -q -r lemma -ll` | Passed: no medium/high findings. |
| `.venv/bin/bandit -q -r lemma` | Failed only on 20 low-severity findings. |
| `.venv/bin/pip-audit --ignore-vuln PYSEC-2025-49 --ignore-vuln PYSEC-2022-42969` | Passed with `No known vulnerabilities found, 3 ignored`; local package `lemma` is not on PyPI and could not be audited as a PyPI dependency. |

---

## Summary verdict

Lemma is materially stronger than the prior 7.2 audit baseline. The core live
rule remains simple: **valid Lean proof passes, invalid proof fails**. The latest
pass improved the surrounding failure boundaries so local validator problems
are less likely to masquerade as miner proof failures or block already-computed
weights.

The next points toward 10 are evidence-heavy rather than code-heavy: confirm the
saved head in GitHub Actions, collect live testnet measurements, keep deleting
stale research/live compatibility surfaces, and invite external review once the
testnet path is stable.
