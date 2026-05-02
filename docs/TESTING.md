# Testing

Requires a cloned repo and **`uv sync --extra dev`** ([GETTING_STARTED.md](GETTING_STARTED.md)).

## Default suite

```bash
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check lemma tests
```

No API keys required: judges fall back to **`FakeJudge`** when keys are absent; Docker Lean tests stay skipped unless enabled.

## Opt-in Lean tests

| File | Enable |
| ---- | ------ |
| [`test_sandbox_host.py`](../tests/test_sandbox_host.py) | `LEMMA_RUN_HOST_LEAN=1` and `lake` on `PATH` |
| [`test_docker_golden.py`](../tests/test_docker_golden.py) | `RUN_DOCKER_LEAN=1`, Docker, `LEAN_SANDBOX_IMAGE` (e.g. build per below) |

`LEMMA_SKIP_LAKE_CACHE=1` skips `lake exe cache get` when offline.

### Docker golden path

```bash
docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
RUN_DOCKER_LEAN=1 uv run pytest tests/test_docker_golden.py -v
```

CI tags the image `lemma-lean-sandbox:ci`; locally `latest` is sufficient.

## LLM keys

Required only for **`lemma judge`** or live miner/validator runs without **`LEMMA_FAKE_JUDGE`**.
