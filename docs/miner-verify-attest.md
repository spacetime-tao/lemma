# Miner Verify Attest Threat Model

`LEMMA_MINER_VERIFY_ATTEST_ENABLED=1` lets a miner sign a claim that it ran local
Lean verification before returning a proof.

Validators check the signature against the miner hotkey in the metagraph.

The signed message binds:

- protocol magic bytes;
- validator hotkey;
- `theorem_id`;
- `metronome_id`;
- Lean toolchain pin;
- Mathlib revision pin;
- SHA256 of the proof script.

The validator hotkey prevents replay from one validator to another.

## What It Protects

The attest says: this miner hotkey locally verified this proof for this
validator challenge.

If validators lower `LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`, the attest
can reduce validator CPU. Some responses may skip full validator Lean verify for
that round.

Skipped responses stay neutral for verify-credibility updates. Only
validator-run Lean checks improve credibility.

## What It Does Not Protect

This is not hardware remote attestation.

It does not prove:

- the miner used a TEE;
- the miner used a trusted Docker host;
- the miner did not copy a proof;
- the verifier environment was good.

It also does not replace:

- validator spot verification;
- body-hash integrity;
- commit-reveal binding;
- Lean verification as the core rule.

Informal reasoning is outside the live protocol.

## Operator Guidance

Keep:

```text
LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION=1.0
```

until miners reliably run local verification and signatures validate.

If you lower the fraction, set
`LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT`, monitor full-verify failures, and
treat `0.0` as high trust.
