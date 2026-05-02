# Production checklist

Prerequisites: [GETTING_STARTED.md](GETTING_STARTED.md).

## Lean

- Build and pin the sandbox image ([`compose/lean.Dockerfile`](../compose/lean.Dockerfile)) to match catalog **`lean_toolchain`** / **`mathlib_rev`**.
- Set **`LEAN_VERIFY_TIMEOUT_S`**, CPU/memory, **`LEAN_SANDBOX_NETWORK`** for untrusted code.
- Regenerate **`minif2f_frozen.json`** and **`catalog_manifest.json`** when catalog sources change ([GOVERNANCE.md](GOVERNANCE.md)).

## Judge

- Run **`uv run lemma meta`**; distribute **`judge_rubric_sha256`** and **`judge_profile_sha256`**.
- Set **`JUDGE_PROFILE_SHA256_EXPECTED`** to fail on misconfiguration.
- Default stack in **`.env.example`**: Chutes + `Qwen/Qwen3-32B-TEE`. Self-hosted: point `OPENAI_BASE_URL` at vLLM; from containers use a host-reachable URL (`host.docker.internal` on macOS/Windows, bridge gateway on Linux).

## Miner payloads

- Prefer **`reasoning_steps`** + **`proof_script`**; legacy **`reasoning_trace`** supported.
- Cap size with **`SYNAPSE_MAX_TRACE_CHARS`**.
- Align **`DENDRITE_TIMEOUT_S`** across validators (default 3600 s in shipped config).

## Catalogs

- Broader problem sets: [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py) ([CATALOG_SOURCES.md](CATALOG_SOURCES.md)).
- Mathlib overview is a [topic map](https://leanprover-community.github.io/mathlib-overview.html), not a bundled exercise list.

## Training export

**`LEMMA_TRAINING_EXPORT_JSONL`** appends one JSON object per successfully judged miner per epoch. Lemma does not upload files; use cron/systemd/CI and **`scripts/training_export_upload_example.sh`** for object storage or releases.

## Observability

No bundled dashboard. Typical pattern: ship logs or JSONL to storage + BI tools ([FAQ.md](FAQ.md)).

## Ops

Document **`EMPTY_EPOCH_WEIGHTS_POLICY`**, **`SET_WEIGHTS_*`**, **`DENDRITE_TIMEOUT_S`**, registration rules. Monitor **`lemma_epoch_summary`** and **`judge_errors`**.

## Comparator

Optional post-verify hook ([COMPARATOR.md](COMPARATOR.md)): deploy comparator binaries per subnet policy.
