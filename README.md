# Lemma

> **Lemma** — verified reasoning for mathematics on [Bittensor](https://docs.learnbittensor.org/). Miners use **LLMs** (large language models: neural nets trained to generate text/code) to **attack theorems**—here, a *theorem* is a precise logical claim written in **Lean**. They answer by producing a **proof**: Lean source that the kernel checks mechanically. They also submit an **informal** step-by-step explanation (natural language) of how they found that proof. **Validators** run two checks: the proof **either passes** (type-checks against the fixed statement) **or fails**; if it passes, a pinned **LLM judge** scores how clear and faithful the informal trace is, so emissions can compare miners fairly.

Validators verify proofs in **Docker** (lean-sandbox image).

**Status:** The codebase is still largely **proof-of-concept**, but you can **register and run on** **Subnet 467 — Lemma** on **Bittensor testnet** (`--network test`, `NETUID=467` after `lemma configure chain`). **Finney** is Bittensor **mainnet** (a different network). Full copy-paste flow: [getting-started](docs/getting-started.md). Economics, security, and long-term direction: [vision](docs/vision.md).

**First-time path:** [docs/getting-started.md](docs/getting-started.md) — install, keys, `lemma setup`, miner, validator (copy-paste blocks).

## Quick start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra dev
source .venv/bin/activate
lemma
```

`lemma` with no args opens the interactive menu (`setup`, `doctor`, `docs`, …). Create wallets with `btcli` before registering; exact commands are in **getting-started**.

## Docs

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
