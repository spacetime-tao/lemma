# Lemma

Decentralized Bittensor subnet: miners submit **Lean 4 proofs** plus **reasoning traces**; validators verify proofs in a sandboxed Docker environment and score traces via an LLM judge.

## Quick start

`git clone` only copies this repository. Python dependencies (including **Bittensor**, the **`btcli`** tool from the `bittensor[cli]` extra, and the **`lemma` CLI** from this package) are installed by **`uv sync`** into `.venv`.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <this-repository-url>
cd lemma
uv sync --extra dev
source .venv/bin/activate
lemma --help
uv run btcli --help
```

For **`pip`** instead of **uv**: create a venv, then `pip install -e ".[dev]"` from the repo root (same console scripts). Optional extras: **`catalog`** (catalog builders), **`wandb`** — use `uv sync --all-extras` only if you need everything.

Full setup (wallets, `.env`, Docker for validators): [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md).

## Docs

- [Getting started (uv, clone vs sync, wallets, miner vs validator)](docs/GETTING_STARTED.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Production checklist](docs/PRODUCTION.md)
- [Governance & upgrades](docs/GOVERNANCE.md)
- [Comparator hook](docs/COMPARATOR.md)
- [Validator](docs/VALIDATOR.md)
- [Miner](docs/MINER.md)
- [FAQ (subnet primer + Lean/Docker)](docs/FAQ.md)
- [Testing (Lean opt-in, APIs)](docs/TESTING.md)
- [System requirements (miner vs validator)](docs/SYSTEM_REQUIREMENTS.md)
- [Models & Chutes recommendations](docs/MODELS.md)
- [Generated problems (difficulty mix, timeouts)](docs/GENERATED_PROBLEMS.md)
- [Catalog sources (building `minif2f_frozen.json`)](docs/CATALOG_SOURCES.md)

## References

- [Bittensor docs](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F) / [miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0
