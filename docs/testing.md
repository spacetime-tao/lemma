# Testing

Default local checks:

```bash
uv sync --extra dev
uv run ruff check lemma tests
uv run mypy lemma
uv run pytest tests -q
```

No API keys are needed.

## Lean Tests

| File | Enable |
| ---- | ------ |
| [`test_sandbox_host.py`](../tests/test_sandbox_host.py) | `LEMMA_RUN_HOST_LEAN=1` and `lake` on `PATH` |
| [`test_docker_golden.py`](../tests/test_docker_golden.py) | `RUN_DOCKER_LEAN=1`, Docker, `LEAN_SANDBOX_IMAGE` |

Docker golden loop:

```bash
docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
RUN_DOCKER_LEAN=1 uv run pytest tests/test_docker_golden.py -v
```

CI runs the normal suite plus the Docker golden proof check.
