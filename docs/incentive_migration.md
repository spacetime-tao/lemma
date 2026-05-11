# Incentive layer hard-migration

This document tracks **post-audit** mechanism changes in Lemma: proof-centric scoring, same-coldkey partitioning, EMA reputation, expanded templates, and optional protocol hooks (env-gated).

**Active tracker (done vs open):** [workplan.md](workplan.md).

## Implemented (defaults)

| Mechanism | Env / behavior |
|-----------|----------------|
| Proof-only target | A submitted proof must pass Lean verification for the published theorem before it can receive score. See [proof-verification-incentives.md](proof-verification-incentives.md). |
| Identical-payload verify reuse | Same normalized proof payloads can reuse one Lean verification result inside an epoch. This saves validator CPU; it does not remove reward entries. |
| Same-coldkey partition | `LEMMA_SCORING_COLDKEY_PARTITION=1` — after weights are computed, successful hotkeys under the same coldkey share one coldkey allocation. |
| EMA reputation | `LEMMA_REPUTATION_EMA_ALPHA` (default **0.08**); state file `LEMMA_REPUTATION_STATE_PATH` or `~/.lemma/validator_reputation.json`. |
| Verify credibility | `LEMMA_REPUTATION_VERIFY_CREDIBILITY_ALPHA` (default **0.08**) — EMA toward 1.0 on Lean verify pass, 0.0 on fail; persisted with reputation JSON. Applied as `(credibility ** LEMMA_REPUTATION_CREDIBILITY_EXPONENT)` after EMA smoothing. The default exponent is **1.0**; exponent **0** disables the multiplier. See [credibility-exponent-decision.md](credibility-exponent-decision.md). |
| Proof-only live score | A Lean-verified proof enters scoring; a failed proof does not. |
| Multi-theorem epochs | `LEMMA_EPOCH_PROBLEM_COUNT` (default **1**) — sequential challenges per epoch. |
| Judge hardening | Fenced miner blocks + strict single-object JSON rubric parse (anchored rubric spans + skip-invalid candidates when multiple `{...}` fragments appear; repeated valid rubric occurrences fail closed even when identical). |
| Empty-epoch uniform | Validator UID excluded from uniform weights when possible. |
| Response deadline | Miner responses without `deadline_block` fail the integrity gate; responses with `deadline_block` set are dropped if chain head is already at or past that block after the forward returns. |
| Frozen miniF2F catalog | `LEMMA_PROBLEM_SOURCE=frozen` and direct frozen catalog ids require **`LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`** (fail-closed otherwise). |
| Miner verify attest | **`LEMMA_MINER_VERIFY_ATTEST_ENABLED=1`** — miners must run **`LEMMA_MINER_LOCAL_VERIFY=1`**, local Lean PASS, then Sr25519-sign `protocol_attest.miner_verify_attest_message(synapse, validator_hotkey=...)` into **`miner_verify_attest_signature_hex`**. Validators verify against metagraph hotkeys and reject responses whose challenge fields do not match the current theorem/metronome; **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** (default **1.0** = always full Docker verify) selects a deterministic subset for full Lean (lower values reduce validator CPU — trust tradeoff). Threat model: [miner-verify-attest.md](miner-verify-attest.md). |
| Commit-reveal | **`LEMMA_COMMIT_REVEAL_ENABLED=1`** — validator sends two forwards per sub-round: **`commit_reveal_phase=commit`** (miners return **`proof_commitment_hex`**, SHA256 of canonical preimage; see `lemma/protocol_commit_reveal.py`) then **`commit_reveal_phase=reveal`** (full proof + **`commit_reveal_nonce_hex`**). Responses without a matching commit are dropped. Doubles axon round-trip latency vs single-phase. Threat model: [commit-reveal.md](commit-reveal.md). |
| Validator profile peer attest | **`LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED=1`** — after pins match, HTTP GET each URL in **`LEMMA_VALIDATOR_PROFILE_ATTEST_PEER_URLS`** (comma-separated); response must be **plain 64-char hex** or JSON **`{"validator_profile_sha256":"..."}`** equal to this validator’s **`validator_profile_sha256`**. **`LEMMA_VALIDATOR_PROFILE_ATTEST_SKIP=1`** skips peer probes (solo / dev only; logs WARN). Run **`uv run lemma validator profile-attest-serve`** on peers to expose `GET /lemma/validator_profile_sha256`. Legacy `LEMMA_JUDGE_PROFILE_ATTEST_*` env names and `/lemma/judge_profile_sha256` remain accepted as compatibility aliases. Threat model: [validator-profile-attest.md](validator-profile-attest.md). |
| Training export profiles | **`LEMMA_TRAINING_EXPORT_JSONL`** optional JSONL; **`LEMMA_TRAINING_EXPORT_PROFILE`** = **`full`** (proof + optional labels + optional `proof_metrics` + final `pareto_weight`) or **`summary`** (schema v2 — identifiers/provenance without proof, metrics, labels, or weights). See [training_export.md](training_export.md). |
| Generated template RNG | Chain seed is **SHA256-mixed** before template selection (`lemma_generated_rng_v1`) so adjacent seeds pick less correlated templates; **`LEMMA_GENERATED_LEGACY_PLAIN_RNG=1`** restores legacy `Random(seed)`. Problem ids remain **`gen/<chain_seed>`**. |
| Problem seed RPC slack | **`LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS`** pulls chain head back before `resolve_problem_seed` and forward HTTP deadline math — reduces ±1 RPC skew at quantize edges (`lemma/common/problem_seed.py`). |
| Lean workspace cache key | Default **template-only** slot under **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`**; optional **`LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH=1`** appends proof-body fingerprint (`workspace_verify_cache_key` in `lemma/lean/workspace.py`). |
| Toolchain / image pins | Local `lemma/lean-sandbox:latest` is a dev build tag; production operators publish an immutable sandbox ref and set **`LEAN_SANDBOX_IMAGE`** consistently. See [toolchain-image-policy.md](toolchain-image-policy.md). |
| Sybil / identity (documentation) | Same-coldkey partitioning is **not** sybil-proof — see [sybil_economics.md](sybil_economics.md) and [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml). |
| Validator Lean load (documentation) | **`LEMMA_LEAN_VERIFY_MAX_CONCURRENT`**, optional **`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`** when attest on — see [validator_lean_load.md](validator_lean_load.md). |
| Transport (documentation) | Dendrite/Axon + **`LemmaChallenge`** body-hash integrity vs **`computed_body_hash`**; miner responses fail closed when the hash header or deadline block is missing — see [transport.md](transport.md). [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) deprecates Axon-first **new** designs in favor of HTTP + Epistula. |

## Generated registry

Adding templates changes `generated_registry_sha256`. Operators must run `uv run lemma configure subnet-pins` (or update `LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`) after upgrading.

## References

- Scoring: `lemma/scoring/rewards.py`, `lemma/scoring/proof_intrinsic.py`, `lemma/validator/epoch.py`
- Proof intrinsic decision: [proof-intrinsic-decision.md](proof-intrinsic-decision.md)
- Proof verification incentives: [proof-verification-incentives.md](proof-verification-incentives.md)
- Credibility exponent decision: [credibility-exponent-decision.md](credibility-exponent-decision.md)
- Proof fingerprints / coldkey partition: `lemma/scoring/dedup.py`
- Reputation: `lemma/scoring/reputation.py`
- Problem mix: `lemma/problems/generated.py` (`expand_seed_for_problem_rng`), `lemma/common/problem_seed.py` (`mix_sub_problem_seed`)
- Lean cache: `lemma/lean/workspace.py` (`workspace_verify_cache_key`), `lemma/lean/sandbox.py`
- Toolchain and image pins: [toolchain-image-policy.md](toolchain-image-policy.md)
- Sybil / economics (operators): [sybil_economics.md](sybil_economics.md), `knowledge/sybil.realities.yaml`
- Validator throughput: [validator_lean_load.md](validator_lean_load.md)
- Transport / integrity: [transport.md](transport.md), `lemma/protocol.py`
- Miner attest: [miner-verify-attest.md](miner-verify-attest.md), `lemma/protocol_attest.py`, `lemma/miner/forward.py`, `lemma/validator/epoch.py`
- Commit-reveal: [commit-reveal.md](commit-reveal.md), `lemma/protocol_commit_reveal.py`, `lemma/miner/forward.py`, `lemma/validator/epoch.py`
- Validator profile attest: [validator-profile-attest.md](validator-profile-attest.md), `lemma/validator/judge_profile_attest.py`, `lemma/validator/service.py`, `lemma/cli/validator_check.py`
- Training export: `lemma/validator/training_export.py`, `docs/training_export.md`
