# Validator Profile Peer Attest Threat Model

`LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED=1` makes a validator fetch each configured
peer URL and compare the returned `validator_profile_sha256` with its own local
profile hash.

Peers usually expose the hash with:

```bash
uv run lemma validator profile-attest-serve --host 0.0.0.0 --port 8799
```

That serves:

- `GET /lemma/validator_profile_sha256` as plaintext hash,
- `GET /health` as a simple health check.

Peer responses may be either a 64-character hex string or JSON with
`{"validator_profile_sha256":"..."}`.

## What It Protects

This is an operator coordination check. It helps validators notice when their
local scoring profile does not match the peer set they expected to align with.

It catches common mistakes such as:

- different scoring weights or reputation settings,
- different problem cadence or verification policy,
- wrong peer URL,
- stale local config after an upgrade.

The current behavior is all-of-N: every configured peer URL must return the same
hash as this validator, or startup / `lemma validator-check` reports a failure.

## What It Does Not Protect

This is not Byzantine consensus, on-chain attestation, or a cryptographic quorum.

It does not:

- authenticate peers by itself,
- encrypt traffic,
- prevent a network attacker from spoofing plaintext HTTP,
- prove that a peer actually used the profile while scoring,
- handle k-of-n disagreement,
- retry through flaky peer outages,
- replace local `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED` pinning.

Use TLS, private networking, reverse proxies, firewall rules, or another
operator-controlled authentication layer if peer URLs cross an untrusted
network. Signed/on-chain profile attestations or k-of-n checks belong in a
separate design.

## Operator Guidance

Use peer attest when a known validator group wants a simple startup check that
they are running the same scoring profile. Keep the peer URL list small and
intentional. Expect a single unreachable or mismatched URL to fail the check.

`LEMMA_VALIDATOR_PROFILE_ATTEST_SKIP=1` is for solo and development runs only. It
means peer URLs are not checked, so it should not be treated as production
alignment.
