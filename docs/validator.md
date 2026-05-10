# Validator

Walkthrough: [getting-started.md](getting-started.md) — `lemma-cli setup` (validator or both) sets judge and `LEAN_SANDBOX_IMAGE` via prompts. Production validators should use the subnet-published immutable sandbox ref ([toolchain-image-policy.md](toolchain-image-policy.md)).

**Short checklist:** `bash scripts/prebuild_lean_image.sh` → **`lemma-cli rehearsal`** (prover + Lean + judge preview) → `uv run lemma validator-check` until READY → `uv run lemma validator start` (or **validator-check** from `lemma-cli`). Same keys/chain setup as a miner if you run both roles.

Validators **always** wait for subnet epoch boundaries before each round — no timer-only mode; every operator shares the same on-chain cadence.

Validator→miner transport uses Bittensor Dendrite/Axon and synapse body-hash integrity — [transport.md](transport.md).

Judge: Chutes is the live validator path. Anthropic is only for local/experimental judge tooling and requires `uv sync --extra anthropic`.

## Test scoring (simple map)

| What you want | Command |
| --- | --- |
| **End-to-end** preview (prover → Lean → judge) on the live theorem | **`lemma-cli rehearsal`** (default Lean on; `--no-verify` to skip) |
| Exercise **prover** only | `lemma-cli try-prover` (add `--verify` for local Lean) |
| Exercise **judge** alone on text files you saved | `lemma-cli judge --trace reasoning.txt` (optional `--theorem` / `--proof` paths) |
| Rehearse the **full validator** without `set_weights` | `uv run lemma validator dry-run` — rubric step uses **FakeJudge** by default; set **`LEMMA_DRY_RUN_REAL_JUDGE=1`** to bill the real judge during dry-run |
| Only print validator-related env | `lemma-cli validator-config` (not a scoring run) |

`LEMMA_FAKE_JUDGE=1` is accepted only for validator dry-runs; live `uv run lemma validator start` refuses FakeJudge because the subnet expects a real Chutes judge.

## System requirements (Docker)

- **Docker Engine / Docker Desktop** must be installed and **running** whenever **`LEMMA_USE_DOCKER=1`** (default for `uv run lemma validator start`, `uv run lemma verify`, and **`lemma-cli try-prover --verify`**). Lemma talks to the Docker API to **create** a one-shot container per verification job (unless you use a long-lived **`LEMMA_LEAN_DOCKER_WORKER`**); when the job finishes, that container exits.

### Fast Docker verify (sub‑10s warm, still Docker)

Per-job `docker run` adds **hundreds of ms to seconds** of overhead (worse on Docker Desktop). To stay on Docker **and** hit low latency, run a **long-lived worker** container that bind-mounts your workspace cache directory, then set **`LEMMA_LEAN_DOCKER_WORKER`** to that container’s name. Lemma will run **`docker exec`** into it instead of starting a new container each time.

1. Choose a cache directory (same idea as **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`**, e.g. `/var/lib/lemma-lean-cache` on a validator).
2. Start the worker once (match **`LEAN_SANDBOX_IMAGE`** / CPU / memory to production; replace the local `latest` tag below with the published immutable ref):

```bash
docker run -d --name lemma-lean-worker --restart unless-stopped \
  --network none \
  -v /var/lib/lemma-lean-cache:/lemma-workspace:rw \
  lemma/lean-sandbox:latest sleep infinity
```

3. Set **`LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker`** and ensure **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`** (or **`LEMMA_LEAN_DOCKER_WORKER_HOST_ROOT`**) points at the **same host path** you mounted (`/var/lib/lemma-lean-cache`). Inside the container the mount path defaults to **`/lemma-workspace`** — override with **`LEMMA_LEAN_DOCKER_WORKER_MOUNT`** if you used a different mount point.

Requires the **`docker`** CLI on `PATH` for `exec`. CPU/memory limits apply to how you started the worker; each exec inherits that container’s cgroup.

The bundled runtime Docker image is intentionally CLI-light: it talks to the host Docker socket through the Python Docker SDK for one-shot verification, but it does not install the full Docker engine. If you run Lemma itself inside that image, leave **`LEMMA_LEAN_DOCKER_WORKER`** unset unless you build a custom image with a Docker CLI.

**Threads:** Lemma exports **`LEAN_NUM_THREADS`** for host `lake` and inside Docker (Lean’s thread pool; see the [reference](https://lean-lang.org/doc/reference/latest/IO/Tasks-and-Threads/)). Override with **`LEMMA_LEAN_NUM_THREADS`** if your cgroup CPU limit is tight (many threads on a 2‑CPU container can add contention).

**Profiling:** Set **`LEMMA_LEAN_VERIFY_TIMING=1`** for INFO logs with **`docker_exec`** vs **`docker_one_shot`** wall time.

**Compare-only proof metrics:** Set **`LEMMA_LEAN_PROOF_METRICS=1`** to attach experimental `proof_metrics` to `VerifyResult`. This runs one extra Lean `#print` probe after a passing verification and records byte/line counts plus delimiter-count / max-depth shape data. It does **not** affect validator rewards or weights.

**Warm workspace:** When **`LEAN_SANDBOX_NETWORK=bridge`**, Lemma used to run **`lake exe cache get`** on every verify even if Mathlib was already checked out — slow and redundant. It now **skips** that step when **`.lake/packages/mathlib`** exists (override with **`LEMMA_LEAN_ALWAYS_CACHE_GET=1`**). Optional **`LEMMA_LEAN_WORKSPACE_CACHE_INCLUDE_SUBMISSION_HASH=1`** names cache subdirs from proof text so distinct submissions never share one slot (see `lemma/lean/workspace.py`).

**Docker Desktop (macOS):** Bind-mounted caches pay a large FS tax; **`scripts/start_lean_docker_worker.sh`** uses **`:delegated`** on Darwin. For local iteration, host `lake` ( **`LEMMA_ALLOW_HOST_LEAN=1`** + **`lemma-cli try-prover --host-lean`**) can be faster than Docker on a laptop; production validators should run on **Linux + local SSD** — not Docker Desktop on a Mac — for representative latency.

**Bootstrap helper:** `scripts/start_lean_docker_worker.sh` loads `.env` and starts the worker (requires **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`**). Put **`LEMMA_LEAN_DOCKER_WORKER`** in **`.env`** (Lemma reads it via **`LemmaSettings`** — exporting it in the shell alone is not enough unless **`LEMMA_PREFER_PROCESS_ENV=1`**). Use **`./scripts/start_lean_docker_worker.sh --update-dotenv`** to append the line automatically when missing.

**Throughput:** concurrency caps, attest spot-verify fraction (when **`LEMMA_MINER_VERIFY_ATTEST_ENABLED=1`**), and optional remote verify worker — [validator_lean_load.md](validator_lean_load.md).

**One-shot dev warm-up (SSD cache + worker):** from the repo root, **`bash scripts/dev-lean-warm.sh`** creates **`./.lemma-lean-cache`** (unless you already set **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`**), starts the long-lived worker, and with **`--update-dotenv`** appends **`LEMMA_LEAN_DOCKER_WORKER`** when missing. Keep that cache directory between runs so Mathlib and **`.lake`** stay warm.

### Remote Lean verify pool (same operator, second machine)

To keep the **validator VM** light (Axon + orchestration + judge only), run Lean on a **separate** box that shares the same **`.env`** pins (`LEAN_SANDBOX_IMAGE`, cache dir, optional **`LEMMA_LEAN_DOCKER_WORKER`**, etc.):

1. On the worker host: `uv run lemma lean-worker --host 0.0.0.0 --port 8787` (or bind behind an internal LB).
2. On the validator: set **`LEMMA_LEAN_VERIFY_REMOTE_URL=http://<worker>:8787`** (optional **`LEMMA_LEAN_VERIFY_REMOTE_BEARER`** on both sides).

The validator **POSTs** each proof to **`/verify`**; the worker returns the same **`VerifyResult`** JSON as local **`LeanSandbox`**. HTTP read timeout is **`LEAN_VERIFY_TIMEOUT_S`** (including split scaling from the validator) plus **`LEMMA_LEAN_VERIFY_REMOTE_TIMEOUT_MARGIN_S`**.

### Tight seed windows (e.g. ~100 quantize blocks)

Steady-state cost is **incremental `lake build Submission`**, not “Mathlib from scratch,” once the template slot has a warm **`.lake`**. The highest-impact stack (in order):

1. **Fast disk** — put **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`** on local NVMe (not a network share).
2. **Long-lived worker** — **`LEMMA_LEAN_DOCKER_WORKER`** + matching bind mount so verify uses **`docker exec`** (avoids per-job `docker run` overhead).
3. **Thread budget** — set **`LEMMA_LEAN_NUM_THREADS`** so each concurrent verify does not oversubscribe the host. A practical starting point: `≈ max(1, (physical_cores - 1) // LEMMA_LEAN_VERIFY_MAX_CONCURRENT)`; raise concurrency only when CPU, RAM, and Docker keep up.
4. **Parallelism** — increase **`LEMMA_LEAN_VERIFY_MAX_CONCURRENT`** when the machine can run that many sandboxes; lower it if you see OOM, CPU thrash, or Docker stalls.
5. **Platform** — run the validator on **Linux + local SSD**; do not use Docker Desktop on a Mac as your latency reference.
6. **Host `lake` (optional, fastest)** — set **`LEMMA_USE_DOCKER=false`** in **`.env`** when the host’s elan/Lean **toolchain matches** **`LEAN_SANDBOX_IMAGE`**; this removes Docker from the hot path. Confirm with subnet policy (some operators require Docker parity).

**Profiling:** **`LEMMA_LEAN_VERIFY_TIMING=1`** logs wall time for **`docker_exec`** vs one-shot and the active **`LEAN_NUM_THREADS`**.

- You **do not** need to start or **leave idle containers running** in Docker Desktop’s Containers tab. Old **stopped** containers (from earlier runs) are harmless clutter — you can delete them.
- Optional: set **`LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`** to a fast local path so repeat verifies for the **same theorem template** reuse a warm **`.lake`** after the first passing check (see `.env.example`). **`lemma-cli try-prover --verify`** uses **`XDG_CACHE_HOME/lemma-lean-workspace`** by default when unset (override or disable with **`LEMMA_TRY_PROVER_NO_WORKSPACE_CACHE=1`**). That is **on-disk cache**, not “keep a container running all day.” Once primed, Lemma verifies **in the cached slot directory**, so the steady-state cost is mostly **`lake build`** incremental work — on host verify, not Docker startup.

## Lean image

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator dry-run
uv run lemma validator start
```

For a cheap local loop without any inference HTTP, use **`uv run lemma validator dry-run`**, which defaults to FakeJudge in the rubric step. Prefer **`lemma-cli judge --trace …`** to test only the judge stack, or set **`LEMMA_DRY_RUN_REAL_JUDGE=1`** during dry-run when you want to bill the live judge.

## Fingerprints

```bash
uv run lemma meta
```

[governance.md](governance.md).

## Judge profile peer attest (optional)

Some subnets require validators to **agree with peers on the same validator scoring profile**, not only match **`JUDGE_PROFILE_SHA256_EXPECTED`** locally. When **`LEMMA_JUDGE_PROFILE_ATTEST_ENABLED=1`**, startup (and **`uv run lemma validator-check`**) HTTP GETs each URL in **`LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS`** and checks the body matches this process’s **`judge_profile_sha256`** (same fingerprint as **`uv run lemma meta`** / **`lemma-cli configure subnet-pins`**).

| Env | Role |
| --- | --- |
| **`LEMMA_JUDGE_PROFILE_ATTEST_PEER_URLS`** | Comma-separated GET URLs. Response: plain **64-char hex** on the first line, or JSON **`{"judge_profile_sha256":"..."}`**. |
| **`LEMMA_JUDGE_PROFILE_ATTEST_SKIP=1`** | Skip peer HTTP (solo / dev). Logs a **WARN** at validator startup — not for production alignment across validators. |
| **`LEMMA_JUDGE_PROFILE_ATTEST_HTTP_TIMEOUT_S`** | Timeout per URL (default **15**). |

**Expose your hash** for other operators to list in their peer URLs:

```bash
lemma validator judge-attest-serve --host 0.0.0.0 --port 8799
```

Serves **`GET /lemma/judge_profile_sha256`** (`text/plain` hash) and **`GET /health`**. This is operator coordination, not Byzantine consensus or transport security; see [judge-profile-attest.md](judge-profile-attest.md), [.env.example](../.env.example), and [incentive_migration.md](incentive_migration.md).

## Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

## Ops

[production.md](production.md).
