# Testing

Clone repo and `uv sync --extra dev` ([GETTING_STARTED.md](GETTING_STARTED.md)).

## Default suite

```bash
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check lemma tests
```

No API keys needed: `FakeJudge` when keys absent; Docker Lean tests skipped unless enabled.

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

## Generated template gate (CI `docker-lean-sandbox` job)

[`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py) runs `lake build` on every generated template shape. By default it merges all theorems into **one** Lake workspace (single Mathlib build). Set `CI_TEMPLATE_MULTIPLEX=0` to fall back to per-template workspaces (slow; mainly for debugging).

## LLM keys

Only for `lemma judge` or live runs without `LEMMA_FAKE_JUDGE`.
