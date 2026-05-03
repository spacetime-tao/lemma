# Lemma

Bittensor subnet: miners submit Lean 4 proofs and reasoning traces; validators verify in Docker and score traces with an LLM judge.

## Install

| What | You get |
| ---- | ------- |
| `git clone` | Source only. |
| `uv sync` from repo root | `.venv`, editable `lemma` package (CLI `lemma`), `bittensor`, `btcli`. Add `--extra dev` for tests/linters. |

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repository-url>
cd lemma
uv sync --extra dev
source .venv/bin/activate
lemma --help
```

Equivalent: `python -m venv .venv && pip install -e ".[dev]"`. Extras: `catalog`, `wandb` (`uv sync --all-extras` if you need everything).

## New here

After `uv sync --extra dev`, run `lemma` (no args) or `lemma start`. The CLI walks setup: env via `lemma setup`, health via `lemma doctor`, doc paths via `lemma docs`. Optional: `chmod +x scripts/lemma-run` and `./scripts/lemma-run lemma setup` so the wrapper activates `.venv` for you.

Wallet keys: create with `btcli` first. Details: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Documentation

- [Vision & roadmap](docs/VISION.md)
- [Getting started](docs/GETTING_STARTED.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Production](docs/PRODUCTION.md)
- [Governance](docs/GOVERNANCE.md)
- [Comparator](docs/COMPARATOR.md)
- [Validator](docs/VALIDATOR.md)
- [Miner](docs/MINER.md)
- [FAQ](docs/FAQ.md)
- [Testing](docs/TESTING.md)
- [System requirements](docs/SYSTEM_REQUIREMENTS.md)
- [Models](docs/MODELS.md)
- [Generated problems](docs/GENERATED_PROBLEMS.md)
- [Catalog sources](docs/CATALOG_SOURCES.md)

## References

- [Bittensor](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F) / [miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0
