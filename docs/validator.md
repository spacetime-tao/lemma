# Validator Guide

Validators verify submitted Lean proof artifacts against published targets.

## Validator Principle

Score verified proofs, not explanations. The correctness boundary is whether Lean accepts the submitted proof under the published target, toolchain, and policy.

## What Validators Check

Validators should check:

- target registry hash,
- target hash,
- source metadata,
- Lean and mathlib toolchain,
- submission policy,
- proof artifact hash,
- local or worker verification result,
- custody metadata for live reward claims.

For publication-ready proofs, validators or operators should also preserve enough verifier output to support a later proof artifact: target hash, submission hash, policy, toolchain, pass/fail result, and attestation summary.

## What Validators Should Not Score

Validators should not score informal reasoning, private notes, stylistic proof preferences, or claims about intent. Those may be useful for humans, but they are outside the live reward correctness path.

## Docker Verification

Use Docker verification by default:

```bash
docker build -f compose/lean.Dockerfile -t lemma-lean-sandbox:latest .
LEAN_SANDBOX_IMAGE=lemma-lean-sandbox:latest uv run lemma validate --check
```

Host Lean is for local debugging only and requires `LEMMA_ALLOW_HOST_LEAN=1`.

## Optional HTTP Worker

A verifier worker can keep dependencies warm:

```bash
uv run lemma validate --worker --host localhost --port 8787
```

For non-loopback binds, configure `LEMMA_LEAN_VERIFY_REMOTE_BEARER`. Unauthenticated non-loopback binds are refused unless the explicit development override is enabled.

## Workspace Cache

Set `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` for warm Docker or worker verification. Keep cache bounds enabled with:

- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS`
- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES`

The cache is disposable. Do not store secrets or operator notes there.

## Target Issues

If a target has bad source metadata, a mismatched hash, an unsupported policy, or a missing toolchain pin, treat it as a target issue. Do not paper over it in validator scoring.

## Publication Boundary

Validator attestation can make a proof eligible for publication, but upstream PR acceptance is outside validator scoring. Score the exact Lean target; leave upstream review to upstream maintainers.
