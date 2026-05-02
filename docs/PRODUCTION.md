# Production checklist

Prerequisites: [GETTING_STARTED.md](GETTING_STARTED.md).

## Lean

- Build and pin sandbox image ([`compose/lean.Dockerfile`](../compose/lean.Dockerfile)) to match catalog `lean_toolchain` / `mathlib_rev`.
- Set `LEAN_VERIFY_TIMEOUT_S`, CPU/memory, `LEAN_SANDBOX_NETWORK` for untrusted code.
- Regenerate `minif2f_frozen.json` and `catalog_manifest.json` when catalog sources change ([GOVERNANCE.md](GOVERNANCE.md)).

## Judge

- `uv run lemma meta`; distribute `judge_rubric_sha256` and `judge_profile_sha256`.
- `JUDGE_PROFILE_SHA256_EXPECTED` to fail on misconfiguration.
- Default in `.env.example`: Chutes + `Qwen/Qwen3-32B-TEE`. Self-hosted: `OPENAI_BASE_URL` to vLLM; from containers use a host-reachable URL (`host.docker.internal` on macOS/Windows, bridge gateway on Linux).

## Miner payloads

- Prefer `reasoning_steps` + `proof_script`; legacy `reasoning_trace` supported.
- Cap size with `SYNAPSE_MAX_TRACE_CHARS`.
- Align `DENDRITE_TIMEOUT_S` and `LEAN_VERIFY_TIMEOUT_S` across validators (defaults 300 s).
- Choose `LEMMA_VALIDATOR_ROUND_INTERVAL_S` vs `LEMMA_VALIDATOR_ALIGN_ROUNDS_TO_EPOCH` for cadence.

## Catalogs

- Broader sets: [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py) ([CATALOG_SOURCES.md](CATALOG_SOURCES.md)).
- Mathlib overview: [topic map](https://leanprover-community.github.io/mathlib-overview.html).

## Training export

`LEMMA_TRAINING_EXPORT_JSONL` appends one JSON object per successfully judged miner per epoch. Lemma does not upload; use cron/systemd and [`scripts/training_export_upload_example.sh`](../scripts/training_export_upload_example.sh) for storage.

## Observability

No bundled dashboard. Typical: logs or JSONL to storage + BI ([FAQ.md](FAQ.md)).

## Ops

Document `EMPTY_EPOCH_WEIGHTS_POLICY`, `SET_WEIGHTS_*`, `DENDRITE_TIMEOUT_S`, registration rules. Watch `lemma_epoch_summary` and `judge_errors`.

## Comparator

Optional post-verify hook ([COMPARATOR.md](COMPARATOR.md)).
