# Testing

Install dev dependencies first:

```bash
uv sync --extra dev
```

## Default Suite

```bash
uv run pytest tests/ -q
uv run ruff check lemma tests tools
```

No API keys are needed for proof-verification tests. Docker Lean tests are
skipped unless enabled.

## Opt-In Lean Tests

| Test | Enable |
| --- | --- |
| [`test_sandbox_host.py`](../tests/test_sandbox_host.py) | `LEMMA_RUN_HOST_LEAN=1` and `lake` on `PATH`. |
| [`test_docker_golden.py`](../tests/test_docker_golden.py) | `RUN_DOCKER_LEAN=1`, Docker, and `LEAN_SANDBOX_IMAGE`. |

When offline, `LEMMA_SKIP_LAKE_CACHE=1` skips `lake exe cache get`.

## Docker Golden

```bash
docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
RUN_DOCKER_LEAN=1 uv run pytest tests/test_docker_golden.py -v
```

Local `latest` is fine for development. Production should use an immutable image
tag or digest. See [toolchain-image-policy.md](toolchain-image-policy.md).

## Generated Template Gate

CI runs:

```bash
uv run python scripts/ci_verify_generated_templates.py
```

The cheap gate checks that every generated builder is reachable and has coherent
metadata.

With `RUN_DOCKER_LEAN_TEMPLATES=1`, the script also runs `lake build` on every
generated template shape.

Set `CI_TEMPLATE_MULTIPLEX=0` only when debugging per-template workspaces.

## LLM Keys

Only prover preview commands need inference keys:

- `uv run lemma-cli rehearsal`
- `uv run lemma-cli try-prover`

`lemma-cli rehearsal` runs prover plus Lean on the current subnet theorem. Live
scoring still accepts only proofs that pass validator Lean verification.
