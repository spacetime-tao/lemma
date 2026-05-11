# Lemma

> **Lemma: incentivized theorem proving for mathematics on [Bittensor](https://docs.learnbittensor.org/).** Miners submit Lean proof scripts for published theorem statements. Validators mechanically verify those proofs with Lean. A proof that passes verification can be scored; a proof that fails verification cannot.

A **theorem** is the precise claim to establish; a **proof** is the formal, machine-checkable argument that shows it. **Lean** is a proof assistant (and language): it checks those proofs mechanically, line by line. Validators run that check in **Docker** (lean-sandbox image).

## What Lemma Produces

Lemma produces verified formal proofs.

The network publishes theorem statements. Miners spend AI compute searching for
Lean proof scripts. Validators mechanically check those scripts against the
published theorem. If Lean accepts the proof, that theorem/proof pair is the
work product.

That makes Lemma proof mining: similar in spirit to Bitcoin mining, but instead
of producing valid hashes under a difficulty rule, miners produce valid Lean
proofs under a theorem rule.

**Status:** The codebase is still largely **proof-of-concept**, but you can **register and run on** **Subnet 467 — Lemma** on **Bittensor testnet** (`--network test`, `NETUID=467` after `uv run lemma-cli configure chain`). **Finney** is Bittensor **mainnet** (a different network).

## Start Here

1. **Read the litepaper:** [docs/litepaper.md](docs/litepaper.md)
2. **Run the setup path:** [docs/getting-started.md](docs/getting-started.md)
3. **Use the technical reference:** [docs/technical-reference.md](docs/technical-reference.md)

Friendly operator UX lives in
[lemma-cli](https://github.com/spacetime-tao/lemma-cli).

## Quick start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli --extra cli
uv run lemma --help
uv run lemma-cli --help
```

Use one environment and one tool: `uv`. The core Lemma `.venv` owns the subnet
dependencies, and the `cli` extra installs `lemma-cli` as the friendly operator
surface (`setup`, `doctor`, `docs`, …). Create wallets with the `btcli`
command from official [bittensor-cli](https://pypi.org/project/bittensor-cli/);
install it in this repo with `uv sync --extra btcli --extra cli` (or
`uv sync --extra dev --extra btcli --extra cli` for development). See
**getting-started** for PyPI package names vs the `btcli` executable.

**Validator entrypoint:** use **`lemma validator start`** (or Docker `ENTRYPOINT ["lemma"]` / `CMD ["validator", "start"]`).

## Short Docs Index

| Topic | File |
| ----- | ---- |
| Litepaper | [litepaper.md](docs/litepaper.md) |
| Install & operator checklist | [getting-started.md](docs/getting-started.md) |
| Vision & roadmap | [vision.md](docs/vision.md) |
| Components | [architecture.md](docs/architecture.md) |
| Technical reference | [technical-reference.md](docs/technical-reference.md) |
| Miner | [miner.md](docs/miner.md) |
| Validator | [validator.md](docs/validator.md) |
| Models / APIs | [models.md](docs/models.md) |
| Production / ops | [production.md](docs/production.md) |
| VPS safety / key custody | [vps-safety.md](docs/vps-safety.md) |
| Governance / pins | [governance.md](docs/governance.md) |
| Toolchain / image pinning | [toolchain-image-policy.md](docs/toolchain-image-policy.md) |
| Tests | [testing.md](docs/testing.md) |
| Generated problems | [generated-problems.md](docs/generated-problems.md) |
| System requirements | [system-requirements.md](docs/system-requirements.md) |

Deeper design records live in `docs/` for proof rewards, problem supply,
Sybil/reward policy, proof metrics, commit-reveal, and attest behavior.

## References

- [Bittensor](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F) / [miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0
