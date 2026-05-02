# Testing Lemma

From a **[cloned](../README.md) repo** with dependencies installed (**`uv sync --extra dev`** — see [GETTING_STARTED.md](GETTING_STARTED.md)).

## Default (CI / quick)

```bash
uv sync --extra dev
uv run pytest tests/ -q
uv run ruff check lemma tests
```

No **API keys** are required for the default suite: judges use **`FakeJudge`** where keys are absent, and Lean integration tests are **skipped** unless opted in.

## Opt-in Lean integration tests

| Test file | Enable | What it does |
|-----------|--------|----------------|
| [`tests/test_sandbox_host.py`](../tests/test_sandbox_host.py) | `LEMMA_RUN_HOST_LEAN=1` and `lake` on `PATH` (e.g. via [elan](https://github.com/leanprover/elan)) | Host `lake build` + axiom check (~2 min cold, faster with cache). |
| [`tests/test_docker_golden.py`](../tests/test_docker_golden.py) | `RUN_DOCKER_LEAN=1`, Docker, image `LEAN_SANDBOX_IMAGE` (default `lemma/lean-sandbox:latest`) | Same golden path inside Docker (CI builds `lemma-lean-sandbox:ci` and runs this). |

Optional: `LEMMA_SKIP_LAKE_CACHE=1` to skip `lake exe cache get` on hosts without network.

### Docker in plain English

**Docker** is a way to run Lemma inside a **small Linux box** that already has Lean and mathlib baked in, so your Mac doesn’t need to download everything itself.

1. Install **Docker Desktop** for your OS and start it (whale icon in the menu bar should be steady).
2. In a terminal, `cd` to the Lemma repo folder.
3. Build the sandbox image once (can take several minutes):

   ```bash
   docker build -f compose/lean.Dockerfile -t lemma/lean-sandbox:latest .
   ```

4. Run the golden test:

   ```bash
   RUN_DOCKER_LEAN=1 uv run pytest tests/test_docker_golden.py -v
   ```

That’s it: if the test passes, Docker + Lean verification works on your machine the same way CI does (CI uses tag `lemma-lean-sandbox:ci`; locally `latest` is fine).

## LLM / judge API keys

Only needed if you run the real **`lemma judge`** command or validators/miners with **`LEMMA_FAKE_JUDGE` unset** and real providers. Not required for **`pytest`**.
