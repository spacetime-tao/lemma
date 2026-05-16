# Miner Verify Attest Threat Model

`LEMMA_MINER_VERIFY_ATTEST_ENABLED=1` lets a miner sign a statement that it ran
local Lean verification before returning a proof. Validators verify that
signature against the miner hotkey in the metagraph.

The signed preimage is versioned and binds:

- protocol magic bytes,
- validator hotkey,
- `theorem_id`,
- `metronome_id`,
- Lean toolchain pin,
- mathlib revision pin,
- SHA-256 of the submitted proof script.

The validator hotkey binding prevents a signature made for one validator from
being replayed as a valid attest to another validator.

## What It Protects

Miner verify attest is a narrow proof-verification claim: this miner hotkey says
it locally verified this proof for this validator challenge.

When validators lower `LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION`, the
attest can reduce validator CPU by letting some responses skip full validator
Lean verification. Skipped responses remain neutral for verify-credibility
updates; only validator-run Lean verification improves credibility.

Validators still reject responses whose challenge fields do not match the
current theorem, metronome, toolchain pins, or deadline before attest trust can
matter.

## What It Does Not Protect

This is not hardware remote attestation. It does not prove a miner used a TEE,
secure enclave, or trusted Docker host. It is a miner hotkey signature over a
local Lean-verification claim.

It also does not:

- prove the miner did not copy a proof,
- replace validator spot verification,
- replace response body-hash integrity,
- replace commit-reveal payload binding,
- make a bad verifier environment trustworthy.

Informal reasoning is outside the live protocol. Attest stays focused on the
Lean proof check.

## Operator Guidance

Keep `LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_FRACTION=1.0` until miners reliably
run local verification and signatures validate. If you lower the fraction, set a
non-empty `LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT`, monitor full-verify
failures, and treat `0.0` as a high-trust mode.
