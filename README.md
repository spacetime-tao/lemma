# Lemma

Bittensor subnet: miners submit **Lean 4 proofs** and **reasoning traces**; validators verify proofs in Docker and score traces with an LLM judge.

## Install (what gets installed)

| Source | Installs |
| ------ | -------- |
| `git clone` | Repository source only. |
| `uv sync` (from repo root) | **`.venv`**, editable **`lemma`** package (CLI entrypoint `lemma`), **`bittensor`** Python library, and **`btcli`** (wallet/chain CLI via the `bittensor[cli]` extra from PyPI). Optional: `--extra dev` for tests and linters. |

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repository-url>
cd lemma
uv sync --extra dev
source .venv/bin/activate
lemma --help
btcli --help
```

Equivalent: `python -m venv .venv && pip install -e ".[dev]"`. Optional extras: `catalog`, `wandb` (`uv sync --all-extras` if all are required).

Wallets, chain endpoints, and API keys: [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Documentation

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
