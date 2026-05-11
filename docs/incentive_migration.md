# Incentive Layer Migration

This note records mechanism changes after the audit.

The active work tracker is [workplan.md](workplan.md).

## Implemented Defaults

| Mechanism | Behavior |
| --- | --- |
| Proof-only target | A proof must pass Lean for the published theorem before it can receive score. |
| Identical-payload verify reuse | Same proof payloads can reuse one Lean result inside an epoch. Rewards are not dropped. |
| Same-coldkey partition | `LEMMA_SCORING_COLDKEY_PARTITION=1`; one coldkey allocation is split across its successful hotkeys. |
| EMA reputation | `LEMMA_REPUTATION_EMA_ALPHA`, state at `LEMMA_REPUTATION_STATE_PATH` or `~/.lemma/validator_reputation.json`. |
| Verify credibility | Moves toward `1.0` on validator Lean pass and `0.0` on fail. Default exponent is `1.0`. |
| Multi-theorem epochs | `LEMMA_EPOCH_PROBLEM_COUNT`, default `1`. |
| Response deadline | Missing or expired `deadline_block` fails the response. |
| Frozen catalog guard | `LEMMA_PROBLEM_SOURCE=frozen` requires `LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`. |
| Miner verify attest | Optional signed claim that the miner ran local Lean. See [miner-verify-attest.md](miner-verify-attest.md). |
| Commit-reveal | Optional two-phase proof binding. See [commit-reveal.md](commit-reveal.md). |
| Validator profile peer attest | Optional peer hash check. See [validator-profile-attest.md](validator-profile-attest.md). |
| Training export | Optional JSONL with `full` or `summary` profile. See [training_export.md](training_export.md). |
| Generated template RNG | Chain seed is SHA256-mixed before template selection. |
| Problem seed RPC slack | `LEMMA_PROBLEM_SEED_CHAIN_HEAD_SLACK_BLOCKS` can reduce one-block RPC skew. |
| Lean workspace cache key | Default cache key is template-only; optional submission hash can be included. |
| Toolchain image pins | Production uses immutable `LEAN_SANDBOX_IMAGE`. |
| Transport integrity | Dendrite/Axon plus `LemmaChallenge` body-hash checks. |

## Generated Registry

Adding generated templates changes `generated_registry_sha256`.

After upgrading, operators must run:

```bash
uv run lemma-cli configure subnet-pins
```

or update:

```text
LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED
```

## References

- [proof-verification-incentives.md](proof-verification-incentives.md)
- [credibility-exponent-decision.md](credibility-exponent-decision.md)
- [proof-intrinsic-decision.md](proof-intrinsic-decision.md)
- [sybil_economics.md](sybil_economics.md)
- [validator_lean_load.md](validator_lean_load.md)
- [transport.md](transport.md)
