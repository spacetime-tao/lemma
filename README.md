# Lemma

Bittensor subnet: miners submit **Lean 4** proofs and reasoning traces; validators verify in Docker and score traces with an LLM judge.

**First-time path:** open [docs/getting-started.md](docs/getting-started.md) — install, keys, `lemma setup`, miner, validator (all copy-paste blocks). **Direction:** [docs/vision.md](docs/vision.md).

## Quick start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repository-url>
cd lemma
uv sync --extra dev
source .venv/bin/activate
lemma
```

`lemma` with no args opens the interactive menu (`setup`, `doctor`, `docs`, …). Create wallets with `btcli` before registering; exact commands are in **getting-started**.

## Docs (lowercase filenames)

| Topic | File |
| ----- | ---- |
| Install & operator checklist | [getting-started.md](docs/getting-started.md) |
| Vision & roadmap | [vision.md](docs/vision.md) |
| Components | [architecture.md](docs/architecture.md) |
| FAQ (timeouts, seeds, scoring) | [faq.md](docs/faq.md) |
| Miner | [miner.md](docs/miner.md) |
| Validator | [validator.md](docs/validator.md) |
| Models / APIs | [models.md](docs/models.md) |
| Production / ops | [production.md](docs/production.md) |
| Governance / pins | [governance.md](docs/governance.md) |
| Tests | [testing.md](docs/testing.md) |
| Comparator hook | [comparator.md](docs/comparator.md) |
| Generated problems | [generated-problems.md](docs/generated-problems.md) |
| Catalog sources | [catalog-sources.md](docs/catalog-sources.md) |
| System requirements | [system-requirements.md](docs/system-requirements.md) |

## References

- [Bittensor](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F) / [miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0
