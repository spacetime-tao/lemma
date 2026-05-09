# Lemma

> **Lemma: Verified reasoning for mathematics on [Bittensor](https://docs.learnbittensor.org/).** Miners use LLMs to solve theorems by writing proofs, and offering an informal, step-by-step explanation. Validators grade the proof (it either passes or it fails) and they grade the quality of the informal reasoning response.

A **theorem** is the precise claim to establish; a **proof** is the formal, machine-checkable argument that shows it. **Lean** is a proof assistant (and language): it checks those proofs mechanically, line by line. Validators run that check in **Docker** (lean-sandbox image).

**Status:** The codebase is still largely **proof-of-concept**, but you can **register and run on** **Subnet 467 — Lemma** on **Bittensor testnet** (`--network test`, `NETUID=467` after `lemma-cli configure chain`). **Finney** is Bittensor **mainnet** (a different network). Full copy-paste flow: [getting-started](docs/getting-started.md). Economics, security, and long-term direction: [vision](docs/vision.md).

**First-time path:** [docs/getting-started.md](docs/getting-started.md) — install, keys, `lemma-cli setup`, miner, validator (copy-paste blocks). Friendly operator UX lives in [lemma-cli](https://github.com/spacetime-tao/lemma-cli).

## Quick start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra dev
source .venv/bin/activate
lemma --help
```

`lemma` alone prints **command help** (like `btcli`). Use the separate **[lemma-cli](https://github.com/spacetime-tao/lemma-cli)** repo for the friendly operator screen (`setup`, `doctor`, `docs`, …). Create wallets with the **`btcli`** command from official **[bittensor-cli](https://pypi.org/project/bittensor-cli/)** (installed via **`bittensor[cli]`** when you `uv sync`—see **getting-started** for PyPI package names vs the `btcli` executable).

**Validator entrypoint:** use **`lemma validator start`** (or Docker `ENTRYPOINT ["lemma"]` / `CMD ["validator", "start"]`). Do **not** run `python validator.py` at the repo root — that file is a **stub** that exits with instructions; the old “burn 100% to UID 0” demo script lives under **`examples/legacy_subnet_burn_validator.py`** only.

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
