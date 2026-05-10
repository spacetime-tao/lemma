# Testing

Clone repo and `uv sync --extra dev` ([getting-started.md](getting-started.md)).

## Default suite

```bash
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check lemma tests
```

No API keys needed for validator dry-runs: they use `FakeJudge` by default; Docker Lean tests are skipped unless enabled.

## Opt-in Lean tests

| File | Enable |
| ---- | ------ |
| [`test_sandbox_host.py`](../tests/test_sandbox_host.py) | `LEMMA_RUN_HOST_LEAN=1` and `lake` on `PATH` |
| [`test_docker_golden.py`](../tests/test_docker_golden.py) | `RUN_DOCKER_LEAN=1`, Docker, `LEAN_SANDBOX_IMAGE` |

`LEMMA_SKIP_LAKE_CACHE=1` skips `lake exe cache get` when offline.

### Docker golden

```bash
docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
RUN_DOCKER_LEAN=1 uv run pytest tests/test_docker_golden.py -v
```

CI uses tag `lemma-lean-sandbox:ci`; locally `latest` is fine.
Production should use a subnet-published immutable tag or digest, not the mutable local `latest` tag ([toolchain-image-policy.md](toolchain-image-policy.md)).

## Generated template gate (CI `docker-lean-sandbox` job)

[`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py) always runs the cheap metadata gate: every generated builder must be reachable, have coherent registry metadata, and bridge the expected theorem name. With `RUN_DOCKER_LEAN_TEMPLATES=1`, it also runs `lake build` on every generated template shape. By default it merges all theorems into **one** Lake workspace (single Mathlib build). Set `CI_TEMPLATE_MULTIPLEX=0` to fall back to per-template workspaces (slow; mainly for debugging).

## LLM keys

Only for `lemma-cli judge`, **`lemma-cli rehearsal`**, or live runs without `LEMMA_FAKE_JUDGE`.

`lemma-cli rehearsal` runs **prover + Lean (default) + judge** on the current subnet theorem (chain RPC required). `lemma-cli judge` scores a **file** of informal reasoning: `lemma-cli judge --trace path/to/trace.txt` (optional `--theorem` / `--proof` files). See `lemma-cli judge --help`. Validator **`dry-run`** uses **FakeJudge** in the rubric step by default; **`LEMMA_DRY_RUN_REAL_JUDGE=1`** turns on live judge there while still skipping `set_weights`.
