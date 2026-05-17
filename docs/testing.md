# Testing

Run the Python checks:

```bash
uv run ruff check lemma tests
uv run mypy lemma
uv run pytest tests -q
```

Run Docker Lean verification after building the sandbox image:

```bash
docker build -f compose/lean.Dockerfile -t lemma-lean-sandbox:ci .
LEAN_SANDBOX_IMAGE=lemma-lean-sandbox:ci RUN_DOCKER_LEAN=1 uv run pytest tests/test_docker_golden.py -v
```

Run reward custody contract checks:

```bash
cd contracts
npm test
npm run compile
```

Useful focused tests:

```bash
uv run pytest tests/test_bounty_cli.py tests/test_bounty_escrow.py -q
uv run pytest tests/test_sandbox_host.py tests/test_verify_runner_remote.py -q
uv run pytest tests/test_submission_policy.py tests/test_problem_codec.py -q
```
