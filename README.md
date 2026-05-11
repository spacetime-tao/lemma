# Lemma

**Lemma** is a [Bittensor](https://docs.learnbittensor.org/) subnet that rewards miners who solve **published math problems**. You respond with **machine-checkable solutions**—**i.e., a proof**: each step is explicit enough that software can verify the whole argument and return a clear yes or no. That is different from winning on rhetoric or intuition alone.

Each round the subnet **publishes** a statement to prove. Miners **submit** candidate proofs. **Validators** run the same automated checker so everyone gets the same pass-or-fail answer. That verification runs in **Docker** so different machines agree. Subnet policy maps accepted proofs to **weights** and **alpha**.

**Bitcoin** is an analogy people already know: miners compete under fixed rules for block rewards. Lemma uses the same broad shape—open competition, shared rules, on-chain incentives—but the job is to produce a **correct proof** of the published problem, not to grind hashes.

**Status:** Software is still largely **proof-of-concept**. Lemma runs on **Bittensor testnet** as **Subnet 467** (`--network test`, `NETUID=467` after `uv run lemma configure chain`). **Alpha on testnet** follows testnet emissions; **mainnet (Finney) alpha** only applies if a Lemma deployment is registered there with live emissions—verify network and netuid for your deployment.

## Start Here

1. **Read the litepaper:** [docs/litepaper.md](docs/litepaper.md)
2. **Skim the FAQ:** [docs/faq.md](docs/faq.md)
3. **Run the setup path:** [docs/getting-started.md](docs/getting-started.md)
4. **Use the technical reference:** [docs/technical-reference.md](docs/technical-reference.md)

## Quick start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
```

Use one environment and one tool: `uv`. The core Lemma `.venv` owns the subnet
dependencies and the `lemma` command (`setup`, `doctor`, `preview`, miner, and
validator). Create wallets with the `btcli` command from official
[bittensor-cli](https://pypi.org/project/bittensor-cli/); install it in this
repo with `uv sync --extra btcli` (or `uv sync --extra dev --extra btcli` for
development).

**Validator entrypoint:** use **`lemma validator start`** (or Docker `ENTRYPOINT ["lemma"]` / `CMD ["validator", "start"]`).

**Docker Compose:** the sample [`docker-compose.yml`](docker-compose.yml) mounts the host **`/var/run/docker.sock`** into the validator service so it can run Lean in Docker. That is powerful—compromise of the validator workload can pivot to the Docker daemon and thus the host. Treat the machine like production infrastructure: firewall the axon, patch Docker, and limit who can reach the API (see [production.md](docs/production.md)).

## Short Docs Index

| Topic | File |
| ----- | ---- |
| Litepaper | [litepaper.md](docs/litepaper.md) |
| FAQ (lay readers) | [faq.md](docs/faq.md) |
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
