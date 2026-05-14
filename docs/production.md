# Production checklist

Prerequisites: [getting-started.md](getting-started.md).

## Lean

- Build and pin the sandbox image ([`compose/lean.Dockerfile`](../compose/lean.Dockerfile)) to match catalog `lean_toolchain` / `mathlib_rev`; use an immutable production ref for `LEAN_SANDBOX_IMAGE` ([toolchain-image-policy.md](toolchain-image-policy.md)).
- Set `LEAN_VERIFY_TIMEOUT_S`, CPU/memory, `LEAN_SANDBOX_NETWORK` for untrusted code.
- Regenerate `minif2f_frozen.json` and `catalog_manifest.json` when catalog sources change ([governance.md](governance.md)).

## Validator profile

- `uv run lemma meta`; distribute `validator_profile_sha256`.
- `LEMMA_VALIDATOR_PROFILE_SHA256_EXPECTED` to fail on misconfiguration.
- Miners: prover can use any operator-chosen host via `PROVER_OPENAI_BASE_URL` / `PROVER_MODEL`; from containers use a host-reachable URL (`host.docker.internal` on macOS/Windows, bridge gateway on Linux).

## Scoring policy

A proof must verify in Lean to enter live scoring. Reputation/credibility may
adjust eligible entries, and same-coldkey hotkeys share that coldkey's allocation
instead of multiplying it.

## Miner payloads

- Require `proof_script`; informal reasoning belongs outside the live protocol.
- Align `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, forward-wait clamps, `LEMMA_LLM_HTTP_TIMEOUT_S`, and `LEAN_VERIFY_TIMEOUT_S` across validators (see `.env.example`).
- Validator cadence follows the published problem-seed mode: quantized theorem windows by default, or subnet epoch boundaries when `LEMMA_PROBLEM_SEED_MODE=subnet_epoch`.

## Catalogs

- Broader sets: [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py) ([catalog-sources.md](catalog-sources.md)).
- Mathlib overview: [topic map](https://leanprover-community.github.io/mathlib-overview.html).

## Training export

`LEMMA_TRAINING_EXPORT_JSONL` appends scored miner rows and one round summary
marker per epoch. Optional **`LEMMA_TRAINING_EXPORT_PROFILE`** controls whether
proof text, proof metrics, and the final `validator_weight` field are included —
see [training_export.md](training_export.md). For proof-metrics calibration, use
`LEMMA_TRAINING_EXPORT_PROFILE=full` with `LEMMA_LEAN_PROOF_METRICS=1`, follow
the [operator checklist](training_export.md#collect-proof-metrics-calibration-data),
and keep exports private. Lemma does not upload private exports; use cron/systemd
and [`scripts/training_export_upload_example.sh`](../scripts/training_export_upload_example.sh)
for private storage.

## Observability

The lightweight local dashboard lives in [`tools/ops_dashboard.py`](../tools/ops_dashboard.py)
and writes a static HTML snapshot from SSH-readable Droplet state. It is
read-only operator tooling, not a scoring component, and should not be
published. For a public page, use [`tools/public_dashboard.py`](../tools/public_dashboard.py)
to render only the deterministic theorem triplet and public miner fields. Do
not serve raw validator logs, private exports, Droplet details, proof scripts,
wallet files, or Lean worker endpoints.

For the public website, use a dedicated summary export:

```bash
LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/public-summary.jsonl
LEMMA_TRAINING_EXPORT_PROFILE=summary
```

Install [`deploy/scripts/lemma-refresh-public-dashboard`](../deploy/scripts/lemma-refresh-public-dashboard)
and the systemd path/timer/service templates in [`deploy/systemd`](../deploy/systemd)
on the validator host to publish `lemmasub.net` after each summary export change,
with a 3-minute timer fallback. That keeps the public dashboard aligned to
validator rounds without putting Git publishing inside the scoring path.

## Ops

Document `SET_WEIGHTS_*`, block-derived forward wait / LLM timeouts, registration rules, rolling scoring settings, and UID-variant status. Watch `lemma_epoch_summary` and scoring/verify errors.

## Cloud / VPS hosts

Running miners or validators on a VPS is allowed operationally, but it changes
the risk profile.

- **Miner on VPS:** common and usually simpler than home networking because the
  axon has a stable public IP and port. Keep the hotkey encrypted, restrict SSH,
  run a firewall, and avoid storing the coldkey private file on the server.
- **Validator on VPS:** use a larger host than a cheap miner box. Validators need
  Docker, Lean caches, and enough RAM/CPU for concurrent verification; a small
  4 GB instance is usually miner-only or test-only.
- **Local machine:** good for development and private keys, but inbound miner
  ports require router/firewall setup and VPNs can hide or change the reachable
  address.
- **Shared host failure:** multiple services on one VPS can all fail together if
  the host, firewall, Docker daemon, or API budget fails. This is fine for tests;
  production operators should monitor and isolate roles as stakes rise.
- **Warm-cache lesson:** the reliable speedup path is a light pinned Lean image,
  persistent workspace cache on fast disk, and a long-lived Docker worker or
  remote worker pool. Testnet measurements saw a simple generated proof around
  292 s cold and 25 s warm on a 4 vCPU / 8 GB shared Linux worker; baked
  all-Mathlib mega-images were brittle in that run.

For production, prefer: coldkey private material offline/local, only hotkeys on
servers, explicit `AXON_EXTERNAL_IP`, explicit firewall rules, systemd or another
supervisor, and regular log review. For a simple operator checklist, see
[vps-safety.md](vps-safety.md). For a step-by-step DigitalOcean guide, see
[droplet-operations.md](droplet-operations.md).

## VPS baseline test sequence

Use this sequence before adding more miner hotkeys or tuning validator shortcuts:

1. Run one miner hotkey on one VPS and one validator on a separate VPS.
2. Record host shape, commit SHA, `lemma meta`, `.env` pins, subnet/netuid, and
   current `btcli subnet show` snapshot.
3. Enable timing logs: `LEMMA_MINER_FORWARD_TIMELINE=1`,
   `LEMMA_LEAN_VERIFY_TIMING=1`, persistent
   `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`, bounded
   `LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS`,
   `LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES`,
   `LEMMA_VALIDATOR_MIN_FREE_BYTES`, and `LEMMA_LEAN_DOCKER_WORKER=1`.
4. Capture cold and warm validator verify times for the same generated theorem.
5. Capture miner forward latency, prover retries/timeouts, axon reachability, and
   validator `lemma_epoch_summary` (`scored=N`, verify failures, set_weights).
6. Add a second miner hotkey only after the single-hotkey path stays online and
   answers inside the validator forward window.

The practical target is not just a local `PASS`; it is miner forwards completing,
validator Lean verification finishing, weights being set, and hotkeys earning
alpha over repeated rounds.

Training/dashboard exports are useful but not consensus-critical. A local JSONL
or public-dashboard write failure should alert the operator without stopping
already-computed grading or `set_weights`. The bundled public dashboard refresh
script serializes itself with `flock`; repeated failures should be treated as an
ops alert, not as validator scoring evidence.

## Multiple miner hotkeys on one host

One machine can run several miner hotkeys if each service has its own wallet
hotkey, `AXON_PORT`, logs, and systemd unit. They can share the same checkout and
prover API account, but API rate limits and spend caps should be set
deliberately. If several services run as the same OS user,
`MINER_MAX_FORWARDS_PER_DAY` shares one counter under `~/.lemma/`; a low shared
cap can make every hotkey return 429 for the rest of the UTC day.

For testing, multiple hotkeys under one coldkey are useful for throughput and
same-theorem comparison data. For rewards, Lemma partitions one coldkey's
allocation across its successful hotkeys, so same-coldkey hotkeys should not be
treated as independent economic identities. Separate coldkeys are an independent
economic-identity test and should be labeled as such on testnet.

## Remote Lean verify worker (`lemma lean-worker`)

When `LEMMA_LEAN_VERIFY_REMOTE_URL` points at an HTTP worker:

- **Bind:** Prefer **`127.0.0.1`** on the same host as the consumer; avoid exposing **`0.0.0.0:8787`** on the public internet without a reverse proxy.
- **Auth:** Set matching **`LEMMA_LEAN_VERIFY_REMOTE_BEARER`** on client and worker (Bearer token). The worker refuses unauthenticated non-loopback binds unless **`LEMMA_LEAN_WORKER_ALLOW_UNAUTHENTICATED_NON_LOOPBACK=1`** is set for dev-only exposure.
- **TLS:** The built-in worker is **plain HTTP**. For cross-network use, terminate TLS in front (nginx, Caddy, cloud LB) or keep verify on a private VPC.
- **Health:** `GET /health` on the worker returns JSON `{"status":"ok"}` for probes.

## Docker socket on validator/miner hosts

Processes that can run arbitrary containers (or `docker exec` into pinned workers) effectively have **root on the host**. Pin **`LEAN_SANDBOX_IMAGE`** by immutable tag or digest ([toolchain-image-policy.md](toolchain-image-policy.md)), restrict who can edit `.env`, and treat the Docker socket as a **high-privilege** dependency.

## Independent security review

CI runs linters, tests, `pip-audit`, and `bandit`, but that is **not** a substitute for a focused third-party review of your deployment (Docker socket, remote Lean workers, keys, and networking). Before **high-stakes mainnet** operation or large treasury exposure, budget an independent security assessment appropriate to your threat model.
