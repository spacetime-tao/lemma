# Lemma

**Lemma** is a [Bittensor](https://docs.learnbittensor.org/) **subnet**. It rewards miners who solve **published math problems** with **machine-checkable proofs**—each step stated clearly enough that software can verify the whole thing and return yes or no.

Each round Lemma **publishes** a statement to prove. **Miners** send candidate proofs. **Validators** run the same **automated checker** so every node gets the same pass-or-fail result. The checker runs in **Docker**—**containers** that bundle the verifier so it behaves the same on different machines. **Weights** are scores validators assign to miners; **alpha** is the reward token—passing proofs feed into payouts through Bittensor’s public rules (details in the [litepaper](docs/litepaper.md)).

**Bitcoin** is a loose comparison: one miner wins each new block; here the competition is about supplying a **correct proof** for the published problem—same broad idea of incentives and open participation, different job.

**Status:** Software is still largely **proof-of-concept**. Lemma runs on **Bittensor testnet** as **Subnet 467** (`--network test`, `NETUID=467` after `uv run lemma configure chain`). **Reward behavior** depends on testnet parameters and registration; **mainnet** (**Finney**) is separate—tokens and rules there only apply if a Lemma deployment is **registered on mainnet**. Always confirm **network** and **netuid**.

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

**Docker Compose:** the sample [`docker-compose.yml`](docker-compose.yml) runs services in containers and mounts the host **`/var/run/docker.sock`** so the validator can start **other** containers for proof checking—high privilege; lock down the host (see [production.md](docs/production.md)). In miner docs, **axon** means the **network endpoint your miner listens on** for validator requests (Bittensor’s term—open the port deliberately).

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
