# Production checklist

Prerequisites: [getting-started.md](getting-started.md).

## Lean

- Build and pin the sandbox image ([`compose/lean.Dockerfile`](../compose/lean.Dockerfile)) to match catalog `lean_toolchain` / `mathlib_rev`; use an immutable production ref for `LEAN_SANDBOX_IMAGE` ([toolchain-image-policy.md](toolchain-image-policy.md)).
- Set `LEAN_VERIFY_TIMEOUT_S`, CPU/memory, `LEAN_SANDBOX_NETWORK` for untrusted code.
- Regenerate `minif2f_frozen.json` and `catalog_manifest.json` when catalog sources change ([governance.md](governance.md)).

## Judge

- `uv run lemma meta`; distribute `judge_rubric_sha256` and `judge_profile_sha256` (judge stack plus deterministic scoring/cadence/verification policy).
- `JUDGE_PROFILE_SHA256_EXPECTED` to fail on misconfiguration.
- Validators: Chutes `OPENAI_BASE_URL` + `OPENAI_MODEL=deepseek-ai/DeepSeek-V3.2-TEE` (enforced; no vLLM for the judge). Miners: prover can use a different host via `PROVER_OPENAI_BASE_URL` / `PROVER_MODEL` as needed; from containers use a host-reachable URL (`host.docker.internal` on macOS/Windows, bridge gateway on Linux).

## Miner payloads

- Prefer `reasoning_steps` + `proof_script`; legacy `reasoning_trace` supported.
- Cap size with `SYNAPSE_MAX_TRACE_CHARS`.
- Align `LEMMA_BLOCK_TIME_SEC_ESTIMATE`, forward-wait clamps, `LEMMA_LLM_HTTP_TIMEOUT_S`, and `LEAN_VERIFY_TIMEOUT_S` across validators (see `.env.example`).
- Validator cadence is subnet epoch boundaries only (mandatory).

## Catalogs

- Broader sets: [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py) ([catalog-sources.md](catalog-sources.md)).
- Mathlib overview: [topic map](https://leanprover-community.github.io/mathlib-overview.html).

## Training export

`LEMMA_TRAINING_EXPORT_JSONL` appends one JSON object per successfully judged miner per epoch. Optional **`LEMMA_TRAINING_EXPORT_PROFILE`** (`full` vs `reasoning_only`) controls whether proof, judge rubric, and Pareto weights are included — see [training_export.md](training_export.md). For proof-metrics calibration, use `LEMMA_TRAINING_EXPORT_PROFILE=full` with `LEMMA_LEAN_PROOF_METRICS=1`, follow the [operator checklist](training_export.md#collect-proof-metrics-calibration-data), and keep exports private. Lemma does not upload; use cron/systemd and [`scripts/training_export_upload_example.sh`](../scripts/training_export_upload_example.sh) for storage.

## Observability

No bundled dashboard. Typical: logs or JSONL to storage + BI ([faq.md](faq.md)).

## Ops

Document `EMPTY_EPOCH_WEIGHTS_POLICY`, `SET_WEIGHTS_*`, block-derived forward wait / LLM timeouts, registration rules. Watch `lemma_epoch_summary` and `judge_errors`.

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

For production, prefer: coldkey private material offline/local, only hotkeys on
servers, explicit `AXON_EXTERNAL_IP`, explicit firewall rules, systemd or another
supervisor, and regular log review.

## Multiple miner hotkeys on one host

One machine can run several miner hotkeys if each service has its own wallet
hotkey, `AXON_PORT`, logs, and systemd unit. They can share the same checkout and
prover API account, but API rate limits and spend caps should be set
deliberately. If several services run as the same OS user,
`MINER_MAX_FORWARDS_PER_DAY` shares one counter under `~/.lemma/`; a low shared
cap can make every hotkey return 429 for the rest of the UTC day.

For testing, multiple hotkeys under one coldkey are useful for throughput and
same-theorem comparison data. For rewards, Lemma's default coldkey dedup keeps
only the best hotkey per coldkey in the final weight calculation, so same-coldkey
hotkeys should not be treated as independent economic identities. Separate
coldkeys are a sybil/economics experiment and should be labeled as such on
testnet.

## Remote Lean verify worker (`lemma lean-worker`)

When `LEMMA_LEAN_VERIFY_REMOTE_URL` points at an HTTP worker:

- **Bind:** Prefer **`127.0.0.1`** on the same host as the consumer; avoid exposing **`0.0.0.0:8787`** on the public internet without a reverse proxy.
- **Auth:** Set matching **`LEMMA_LEAN_VERIFY_REMOTE_BEARER`** on client and worker (Bearer token).
- **TLS:** The built-in worker is **plain HTTP**. For cross-network use, terminate TLS in front (nginx, Caddy, cloud LB) or keep verify on a private VPC.
- **Health:** `GET /health` on the worker returns JSON `{"status":"ok"}` for probes.

## Docker socket on validator/miner hosts

Processes that can run arbitrary containers (or `docker exec` into pinned workers) effectively have **root on the host**. Pin **`LEAN_SANDBOX_IMAGE`** by immutable tag or digest ([toolchain-image-policy.md](toolchain-image-policy.md)), restrict who can edit `.env`, and treat the Docker socket as a **high-privilege** dependency.
