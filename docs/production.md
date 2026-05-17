# Production Verification

Production Lemma has four moving pieces: the target registry, Lean verification, reward custody, and optional proof publication.

## 1. Target Registry

Publish candidate targets freely, but mark them as candidates. Publish live reward-backed targets only after custody metadata and custody state agree.

Pin source metadata, target hashes, policy versions, and toolchain IDs. Validators should reject mismatches rather than guessing.

## 2. Docker Verifier

Use Docker verification by default. The sandbox image pins the Lean and mathlib environment used to check `Submission.lean`.

```bash
docker build -f compose/lean.Dockerfile -t lemma-lean-sandbox:latest .
LEAN_SANDBOX_IMAGE=lemma-lean-sandbox:latest uv run lemma validate --check
```

Host Lean is for local debugging only and requires `LEMMA_ALLOW_HOST_LEAN=1`.

## 3. Optional HTTP Worker

A verifier worker can keep Lean dependencies warm and serve `/verify`:

```bash
uv run lemma validate --worker --host localhost --port 8787
```

For any non-loopback bind, set `LEMMA_LEAN_VERIFY_REMOTE_BEARER`. Unauthenticated non-loopback binds are refused unless the explicit development override is enabled.

Point clients at the worker with `LEMMA_LEAN_VERIFY_REMOTE_URL` and `LEMMA_LEAN_VERIFY_REMOTE_BEARER`.

## 4. Workspace Cache

Set `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` for warm Docker or worker verification. Keep bounds enabled:

- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS`
- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES`

The cache is disposable. Do not store secrets or operator notes there.

## 5. Reward Custody

Publish a target as a live reward only after the registry row and custody contract state agree on chain id, contract address, custody reward id, and funding confirmation.

The CLI builds unsigned transaction data. Operators should inspect, sign, and submit transactions with normal wallet tooling.

## 6. Proof Publication

After a proof verifies and receives the required attestation, operators can publish a canonical proof artifact and prepare an upstream PR package for human review.

The publication path should be manual or review-gated until artifact hosting and PR automation are proven. Do not claim PR automation is live, an artifact URL is stable, or a PR has been opened unless that is true.

Reward settlement remains independent from upstream acceptance.

## 7. Security Checklist

Do not publish local environment files, credentials, deployment notes, machine paths, hostnames, network addresses, logs, caches, or local handoff state.

If a sensitive file is already tracked, remove it from Git tracking while keeping the local copy.
