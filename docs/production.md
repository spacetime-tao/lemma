# Production Verification

Production Lemma needs only three moving pieces: the bounty registry, the escrow contract, and Lean verification.

## Verifier

Use Docker verification by default. The sandbox image pins the Lean and Mathlib environment used to check `Submission.lean`.

```bash
docker build -f compose/lean.Dockerfile -t lemma-lean-sandbox:latest .
LEAN_SANDBOX_IMAGE=lemma-lean-sandbox:latest uv run lemma validate --check
```

Host Lean is for local debugging only and requires `LEMMA_ALLOW_HOST_LEAN=1`.

## Optional HTTP Worker

A verifier worker can keep Lean dependencies warm and serve `/verify`:

```bash
uv run lemma validate --worker --host localhost --port 8787
```

For any non-loopback bind, set `LEMMA_LEAN_VERIFY_REMOTE_BEARER`. Unauthenticated non-loopback binds are refused unless the explicit development override is enabled.

Point clients at the worker with `LEMMA_LEAN_VERIFY_REMOTE_URL` and `LEMMA_LEAN_VERIFY_REMOTE_BEARER`.

## Workspace Cache

Set `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR` for warm Docker or worker verification. Keep bounds enabled:

- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS`
- `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES`

The cache is disposable. Do not store secrets or operator notes there.

## Escrow

Publish only funded escrow-backed bounties as live rewards. The registry row and contract state should agree on chain id, contract address, and escrow bounty id.

The CLI builds unsigned transaction data. Operators should inspect, sign, and submit transactions with their normal wallet tooling.
