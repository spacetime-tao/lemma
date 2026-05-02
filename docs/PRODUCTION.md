# Production readiness (Lemma)

Use this as an operator checklist when moving from dev to a live subnet. First-time machine setup (clone, **`uv sync`**, wallets, **`.env`**): [GETTING_STARTED.md](GETTING_STARTED.md).

## Objective gate (Lean)

- Build and pin the **sandbox image** (`compose/lean.Dockerfile`) so `lake build` matches catalog **`lean_toolchain`** / **`mathlib_rev`** rows.
- Set **`LEAN_VERIFY_TIMEOUT_S`**, Docker CPU/memory, and **`LEAN_SANDBOX_NETWORK`** appropriately for untrusted code.
- Regenerate **`lemma/problems/minif2f_frozen.json`** when bumping sources; keep **`catalog_manifest.json`** in sync ([GOVERNANCE.md](GOVERNANCE.md)).

## Subjective gate (judge)

- Run **`uv run lemma meta`** on a reference machine; distribute **`judge_rubric_sha256`** and **`judge_profile_sha256`**.
- Set **`JUDGE_PROFILE_SHA256_EXPECTED`** on validators so configuration drift fails fast.
- Default judge stack targets **[Chutes](https://chutes.ai/)** (`OPENAI_BASE_URL=https://llm.chutes.ai/v1`, `OPENAI_MODEL=Qwen/Qwen3-32B-TEE`). For self-hosted vLLM, point **`OPENAI_BASE_URL`** at your server; from Dockerized validators use a host-reachable URL (e.g. `host.docker.internal`), not bare `127.0.0.1`.

## Miner responses (PRM-style steps)

- Miners should return **`reasoning_steps`** (array of `{text, title?}`) plus **`proof_script`**. The protocol still accepts a flat **`reasoning_trace`** for compatibility.
- Enforce size with **`SYNAPSE_MAX_TRACE_CHARS`** (steps + titles + legacy trace share one budget after the prover runs).
- **`DENDRITE_TIMEOUT_S`** should cover **LLM prover latency** for hard templates (shipped default **3600s** / 60 minutes); align across validators.

## Dataset breadth (multi-topic math)

- The [mathlib overview](https://leanprover-community.github.io/mathlib-overview.html) lists topic areas covered by the library; it is a **roadmap**, not a downloadable exercise bank.
- Grow volume with **`scripts/build_lemma_catalog.py`** (`yangky`, `dm`, `putnam`, FormalMATH via `uv sync --extra catalog`, mathlib sampling with `--mathlib-root`, `--merge-json`, `--extra-repo`). Rebuilt catalogs include a **`topic`** field per source for stratification ([CATALOG_SOURCES.md](CATALOG_SOURCES.md)).
- Add finer-grained labels by editing merged JSON or **`--merge-json`** fragments (optional keys land in [`Problem.extra`](../lemma/problems/base.py)).

## Training export (PRM JSONL)

- Set **`LEMMA_TRAINING_EXPORT_JSONL`** to a file path. Each epoch appends one JSON object per **successfully judged** miner: `theorem_id`, **`model_card`** (prover id string from the miner), `reasoning_steps`, `reasoning_text`, `proof_script`, `rubric`, `pareto_weight`, `block`, `uid`. Safe to rotate/truncate the file under your retention policy.

### Publishing JSONL off-box (Lemma does not auto-upload)

Lemma **only appends to disk**. To push data daily (e.g. **00:00 UTC**), use **cron**, **systemd timers**, or **CI** with **`aws`**, **`rclone`**, or **`gh release upload`**. See **[`scripts/training_export_upload_example.sh`](../scripts/training_export_upload_example.sh)** for a minimal template: set **`LEMMA_TRAINING_EXPORT_JSONL`**, **`TRAINING_EXPORT_UPLOAD_DEST`** (e.g. `s3://bucket/prefix/$(date -u +%F).jsonl` from cron), and **`TRAINING_EXPORT_UPLOAD_BACKEND`** (`aws` default). Incremental “upload after every epoch” is possible too—wrap the same command from a sidecar—but **daily** snapshots avoid hammering object storage every block.

## Where “everyone sees” outputs (no built-in web UI yet)

Lemma does **not** ship a subnet dashboard. Visibility today is:

| What | Where |
| ---- | ----- |
| Per-epoch scores / weights | Validator logs (`lemma_epoch_summary`, `set_weights` lines). |
| Training-quality rows | **`LEMMA_TRAINING_EXPORT_JSONL`** JSONL on disk (or sync that file to object storage). |
| Chain-level emissions / metagraph | External explorers and [Bittensor](https://docs.learnbittensor.org/) tooling (e.g. community dashboards, Tao.app-style listings). |

**Possible dashboards (you wire them):** ship JSONL to **S3 + Athena**, **BigQuery**, or **ClickHouse** and connect **Metabase** / **Grafana**; or stream logs to **Loki** / **Datadog** and chart `lemma_epoch_summary`. A small custom **Next.js** site can read the JSONL API you expose—nothing in-repo blocks that.

## Chain and ops

- Document **`EMPTY_EPOCH_WEIGHTS_POLICY`**, **`SET_WEIGHTS_*`** retries, **`DENDRITE_TIMEOUT_S`**, and wallet registration expectations for miners.
- Monitor **`lemma_epoch_summary`** logs: verified count, scored count, **`judge_errors`**.

## Optional comparator hook

- See [COMPARATOR.md](COMPARATOR.md): enable **`LEMMA_COMPARATOR_ENABLED`** + **`LEMMA_COMPARATOR_CMD`** to run a post-verify binary in the Lean workspace (experimental). Full **landrun** / comparator rig parity with [lean-eval](https://github.com/leanprover/lean-eval) remains operator-specific.
