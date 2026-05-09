# Incentive layer hard-migration

This document tracks **post-audit** mechanism changes in Lemma: proof-centric scoring, deduplication, EMA reputation, expanded templates, and optional protocol hooks (env-gated).

**Checklist (done vs open):** [incentive-roadmap.md](incentive-roadmap.md).

## Implemented (defaults)

| Mechanism | Env / behavior |
|-----------|----------------|
| Proof + judge blend | `LEMMA_SCORE_PROOF_WEIGHT` (default **0.10** intrinsic / **0.90** judge composite); tune per subnet policy. See [proof-intrinsic-decision.md](proof-intrinsic-decision.md) before changing defaults. |
| Identical submission dedup | `LEMMA_SCORING_DEDUP_IDENTICAL=1` — same `(theorem, proof, trace)` keeps best score. |
| Coldkey dedup | `LEMMA_SCORING_COLDKEY_DEDUP=1` — one hotkey per coldkey (metagraph). |
| EMA reputation | `LEMMA_REPUTATION_EMA_ALPHA` (default **0.08**); state file `LEMMA_REPUTATION_STATE_PATH` or `~/.lemma/validator_reputation.json`. |
| Verify credibility | `LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA` (default **0.08**) — EMA toward 1.0 on Lean verify pass, 0.0 on fail; persisted with reputation JSON. Applied as `(credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)` after EMA smoothing (exponent **0** disables the multiplier). |
| Proof intrinsic | `LEMMA_SCORE_PROOF_WEIGHT` blend; `LEMMA_PROOF_INTRINSIC_STRIP_COMMENTS` (default **on**) strips Lean `--` / `/- … -/` before the length/`by`-count heuristic. Current stance: low-weight bootstrap signal only; do not extend with more regex padding checks. |
| Multi-theorem epochs | `LEMMA_EPOCH_PROBLEM_COUNT` (default **1**) — sequential challenges per epoch. |
| Judge hardening | Fenced miner blocks + strict single-object JSON rubric parse (anchored rubric spans + skip-invalid candidates when multiple `{...}` fragments appear). |
| Empty-epoch uniform | Validator UID excluded from uniform weights when possible. |
| Response deadline | After each forward, responses with `deadline_block` set are dropped if chain head is already at or past that block (late HTTP completions are not scored). |
| Frozen miniF2F catalog | `LEMMA_PROBLEM_SOURCE=frozen` requires **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (fail-closed otherwise). |
| Miner verify attest | **`LEMMA_MINER_VERIFY_ATTEST_ENABLED=1`** — miners must run **`LEMMA_MINER_LOCAL_VERIFY=1`**, local Lean PASS, then Sr25519-sign `protocol_attest.miner_verify_attest_message(synapse)` into **`miner_verify_attest_signature_hex`**. Validators verify against metagraph hotkeys; **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** (default **1.0** = always full Docker verify) selects a deterministic subset for full Lean (lower values reduce validator CPU — trust tradeoff). |
| Commit–reveal | **`LEMMA_COMMIT_REVEAL_ENABLED=1`** — validator sends two forwards per sub-round: **`commit_reveal_phase=commit`** (miners return **`proof_commitment_hex`**, SHA256 of canonical preimage — see `lemma/protocol_commit_reveal.py`) then **`commit_reveal_phase=reveal`** (full proof + **`commit_reveal_nonce_hex`**). Responses without a matching commit are dropped. Doubles axon round-trip latency vs single-phase. |
| Judge profile peer attest | **`LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1`** — after pins match, HTTP GET each URL in **`LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS`** (comma-separated); response must be **plain 64-char hex** or JSON **`{"judge_profile_sha256":"..."}`** equal to this validator’s **`judge_profile_sha256`**. **`LEMMA_JUDGE_PROFILE_ATTEST_SKIP=1`** skips peer probes (solo / dev; logs WARN). Run **`lemma validator judge-attest-serve`** on peers to expose `GET /lemma/judge_profile_sha256`. Implementation: `lemma/validator/judge_profile_attest.py`. |
| Training export profiles | **`LEMMA_TRAINING_EXPORT_JSONL`** optional JSONL; **`LEMMA_TRAINING_EXPORT_PROFILE`** = **`full`** (proof + rubric + optional `proof_metrics` + `pareto_weight`) or **`reasoning_only`** (schema v2 — trace fields without proof, proof metrics, judge labels, or weights). See [training_export.md](training_export.md). |
| Generated template RNG | Chain seed is **SHA256-mixed** before template selection (`lemma_generated_rng_v1`) so adjacent seeds pick less correlated templates; **`LEMMA_GENERATED_LEGACY_PLAIN_RNG=1`** restores legacy `Random(seed)`. Problem ids remain **`gen/<chain_seed>`**. |
| Problem seed RPC slack | **`LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS`** pulls chain head back before `resolve_problem_seed` and forward HTTP deadline math — reduces ±1 RPC skew at quantize edges (`lemma/common/problem_seed.py`). |
| Lean workspace cache key | Default **template-only** slot under **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`**; optional **`LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH=1`** appends proof-body fingerprint (`workspace_verify_cache_key` in `lemma/lean/workspace.py`). |
| Sybil / identity (documentation) | Coldkey dedup and identical-submission dedup are **not** sybil-proof — see [sybil_economics.md](sybil_economics.md) and [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml). |
| Validator Lean load (documentation) | **`LEMMA_LEAN_VERIFY_MAX_CONCURRENT`**, **`LEMMA_JUDGE_MAX_CONCURRENT`**, optional **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** when attest on — see [validator_lean_load.md](validator_lean_load.md). |
| Transport (documentation) | Dendrite/Axon + **`LemmaChallenge`** body-hash integrity vs **`computed_body_hash`** — see [transport.md](transport.md); [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) deprecates Axon-first **new** designs in favor of HTTP + Epistula. |

## Generated registry

Adding templates changes `generated_registry_sha256`. Operators must run `lemma-cli configure subnet-pins` (or update `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`) after upgrading.

## References

- Scoring: `lemma/scoring/rewards.py`, `lemma/scoring/proof_intrinsic.py`, `lemma/validator/epoch.py`
- Proof intrinsic decision: [proof-intrinsic-decision.md](proof-intrinsic-decision.md)
- Dedup: `lemma/scoring/dedup.py`
- Reputation: `lemma/scoring/reputation.py`
- Problem mix: `lemma/problems/generated.py` (`expand_seed_for_problem_rng`), `lemma/common/problem_seed.py` (`mix_sub_problem_seed`)
- Lean cache: `lemma/lean/workspace.py` (`workspace_verify_cache_key`), `lemma/lean/sandbox.py`
- Sybil / economics (operators): [sybil_economics.md](sybil_economics.md), `knowledge/sybil.realities.yaml`
- Validator throughput: [validator_lean_load.md](validator_lean_load.md)
- Transport / integrity: [transport.md](transport.md), `lemma/protocol.py`
- Miner attest: `lemma/protocol_attest.py`, `lemma/miner/forward.py`, `lemma/validator/epoch.py`
- Commit–reveal: `lemma/protocol_commit_reveal.py`, `lemma/miner/forward.py`, `lemma/validator/epoch.py`
- Judge profile attest: `lemma/validator/judge_profile_attest.py`, `lemma/validator/service.py`, `lemma/cli/validator_check.py`
- Training export: `lemma/validator/training_export.py`, `docs/training_export.md`
