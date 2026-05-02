# Lemma

Decentralized Bittensor subnet: miners submit **Lean 4 proofs** plus **reasoning traces**; validators verify proofs in a sandboxed Docker environment and score traces via an LLM judge.

## Quick start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync --all-extras
source .venv/bin/activate
lemma --help
```

## Docs

- [Getting started (layman guide: uv, wallets, miner vs validator)](docs/GETTING_STARTED.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Production checklist](docs/PRODUCTION.md)
- [Comparator hook](docs/COMPARATOR.md)
- [Validator](docs/VALIDATOR.md)
- [Miner](docs/MINER.md)
- [FAQ (subnet primer + Lean/Docker)](docs/FAQ.md)
- [Testing (Lean opt-in, APIs)](docs/TESTING.md)
- [System requirements (miner vs validator)](docs/SYSTEM_REQUIREMENTS.md)
- [Models & Chutes recommendations](docs/MODELS.md)
- [Generated problems (difficulty mix, timeouts)](docs/GENERATED_PROBLEMS.md)

## References

- [Bittensor docs](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F) / [miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0
