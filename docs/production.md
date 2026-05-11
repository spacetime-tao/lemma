# Production Checklist

Start with [getting-started.md](getting-started.md). This page lists the extra
checks before running real miner or validator services.

## Lean And Docker

- Build the Lean sandbox image from [`compose/lean.Dockerfile`](../compose/lean.Dockerfile).
- Pin `LEAN_SANDBOX_IMAGE` to an immutable tag or digest.
- Match the image to the catalog `lean_toolchain` and `mathlib_rev`.
- Set `LEAN_VERIFY_TIMEOUT_S`, CPU, memory, and `LEAN_SANDBOX_NETWORK`.
- Rebuild catalog files when catalog sources change.

Image policy: [toolchain-image-policy.md](toolchain-image-policy.md).

## Validator Profile

Run:

```bash
uv run lemma meta
```

Share `validator_profile_sha256` with operators. Set
`LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED` when you want startup to fail on
profile drift.

## Scoring Policy

A proof must pass Lean before it can enter live scoring.

After that, reputation, Pareto weighting, and same-coldkey partitioning build
the final weight map.

## Miner Payload

Live miner answers center on `proof_script`. Informal reasoning is outside live
reward scoring.

Keep these aligned across validators:

- `LEMMA_BLOCK_TIME_SEC_ESTIMATE`
- `LEMMA_FORWARD_WAIT_MIN_S`
- `LEMMA_FORWARD_WAIT_MAX_S`
- `LEMMA_LLM_HTTP_TIMEOUT_S`
- `LEAN_VERIFY_TIMEOUT_S`

Validator cadence follows subnet epoch boundaries only.

## Catalogs

Build broader catalogs with:

```bash
uv run python scripts/build_lemma_catalog.py
```

More detail: [catalog-sources.md](catalog-sources.md).

## Training Export

`LEMMA_TRAINING_EXPORT_JSONL` writes one JSON object per scored miner per epoch.

`LEMMA_TRAINING_EXPORT_PROFILE` controls whether proof text, proof metrics, and
Pareto weights are included.

For proof-metrics calibration, keep exports private and use:

```bash
LEMMA_TRAINING_EXPORT_PROFILE=full
LEMMA_LEAN_PROOF_METRICS=1
```

More detail: [training_export.md](training_export.md).

## Observability

There is no bundled dashboard.

At minimum, capture:

- service logs;
- `lemma_epoch_summary`;
- verification failures;
- set-weights results;
- optional JSONL export.

## VPS Hosts

Cloud hosts are fine, but treat them as hotkey machines.

- Put only hotkeys on servers.
- Keep coldkeys local or offline.
- Use explicit `AXON_EXTERNAL_IP`.
- Use firewall rules.
- Run services under systemd or another supervisor.
- Review logs often.

More detail: [vps-safety.md](vps-safety.md).

## VPS Baseline Test

Before adding more hotkeys or shortcuts:

1. Run one miner hotkey and one validator.
2. Record host size, commit SHA, `lemma meta`, `.env` pins, subnet, and netuid.
3. Enable `LEMMA_MINER_FORWARD_TIMELINE=1`.
4. Enable `LEMMA_LEAN_VERIFY_TIMING=1`.
5. Use a persistent `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`.
6. Record cold and warm Lean verify time.
7. Record miner response time, retries, timeouts, and axon reachability.
8. Confirm `set_weights` and emission movement over repeated rounds.

The goal is not just local `PASS`. The goal is live miner responses, finished
Lean checks, weights written, and hotkeys earning over time.

## Multiple Miner Hotkeys

One host can run several miner hotkeys. Each service needs its own:

- wallet hotkey;
- `AXON_PORT`;
- log file;
- service unit.

They can share a checkout and prover API account. Watch API rate limits and
spend caps.

Same-coldkey hotkeys share that coldkey's allocation. Use separate coldkeys only
when testing separate economic identities.

## Remote Lean Worker

When `LEMMA_LEAN_VERIFY_REMOTE_URL` points to a worker:

- bind to `127.0.0.1` on the same host;
- use a private network for cross-host traffic;
- set `LEMMA_LEAN_VERIFY_REMOTE_BEARER`;
- put TLS in front if traffic crosses an untrusted network;
- probe `GET /health`.

## Docker Socket

A process that can run Docker containers is effectively high privilege on that
host.

Pin `LEAN_SANDBOX_IMAGE`, restrict `.env` edits, and limit Docker socket access.
