# Validator Profile Peer Attest Threat Model

`LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED=1` checks that configured peer validators
report the same `validator_profile_sha256`.

Serve your hash with:

```bash
uv run lemma validator profile-attest-serve --host 0.0.0.0 --port 8799
```

It exposes:

- `GET /lemma/validator_profile_sha256`
- `GET /health`

The profile response can be a 64-character hex string or JSON:

```json
{"validator_profile_sha256":"..."}
```

## What It Protects

This is an operator coordination check.

It catches common drift:

- scoring weights differ;
- reputation settings differ;
- problem cadence differs;
- verification policy differs;
- peer URL is wrong;
- local config is stale.

Current behavior is all-of-N. Every configured peer must return this validator's
hash, or startup and `lemma validator-check` report failure.

## What It Does Not Protect

This is not:

- Byzantine consensus;
- on-chain attestation;
- a cryptographic quorum;
- traffic encryption;
- peer authentication by itself.

It does not prove a peer actually used that profile while scoring.

Use TLS, private networking, reverse proxies, firewalls, or another auth layer
for untrusted networks.

## Operator Guidance

Use peer attest for a small known validator group.

Keep the peer list short. Expect one bad or unreachable URL to fail the check.

`LEMMA_VALIDATOR_PROFILE_ATTEST_SKIP=1` is for solo or dev runs only.
