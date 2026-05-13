# Lemma

**Lemma is a [Bittensor](https://docs.learnbittensor.org/) subnet that rewards correct mathematical proofs.**

Every round, Lemma posts a theorem written in Lean. Miners run automated proving
systems. Validators run Lean. The proof passes or it fails.

Bitcoin rewards miners for securing the network. Bittensor rewards miners for
producing useful intelligence. Lemma rewards miners for producing correct
proofs.

A Lemma round is simple:

1. The subnet publishes a theorem statement.
2. Miners submit candidate Lean proof scripts.
3. Validators verify those scripts with the published toolchain.
4. Passing proofs become eligible for downstream scoring and allocation under Lemma's subnet rules; failing proofs do not.

Anything that can be formalized as a Lean statement can become work for Lemma:
algebra, number theory, logic, combinatorics, geometry, computer science,
cryptography, and more.

Lemma is still proof-of-concept software. It currently runs on Bittensor testnet as **subnet 467** (`--network test`; run `uv run lemma configure chain` to set `NETUID=467`). Mainnet, also known as Finney, is separate. Only treat mainnet rewards or tokens as relevant when the deployment you are following is registered, active, and matched to the correct **network** and **netuid**.

For the full mechanism and reward model, start with the [litepaper](docs/litepaper.md).

## Start Here

1. **Understand the mechanism:** [docs/litepaper.md](docs/litepaper.md)
2. **Get plain-language answers:** [docs/faq.md](docs/faq.md)
3. **Install and run Lemma:** [docs/getting-started.md](docs/getting-started.md)
4. **Check implementation details:** [docs/technical-reference.md](docs/technical-reference.md)

## Quick start

To try the CLI locally:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
```

Use one environment and one tool: `uv`. The Lemma `.venv` holds subnet dependencies and the `lemma` command (`setup`, `doctor`, `preview`, miner, validator). Wallets use `btcli` from [bittensor-cli](https://pypi.org/project/bittensor-cli/); install it here with `uv sync --extra btcli` (or `uv sync --extra dev --extra btcli` for development).

**Validators:** start with `lemma validator start` (or Docker `ENTRYPOINT ["lemma"]` / `CMD ["validator", "start"]`).

### Operators

The sample [`docker-compose.yml`](docker-compose.yml) runs Lemma services in containers. It also mounts **`/var/run/docker.sock`** so validators can spawn isolated proof-checking containers. That socket is high privilege. Lock down the host before using this setup in production; see [production.md](docs/production.md).

In the miner docs, **axon** is Bittensor’s term for the network address and port where your miner listens for validator traffic. Open that port intentionally in firewalls and cloud security groups.

## Short Docs Index

| Topic | File |
| ----- | ---- |
| Litepaper | [litepaper.md](docs/litepaper.md) |
| FAQ (lay readers) | [faq.md](docs/faq.md) |
| Install & operator checklist | [getting-started.md](docs/getting-started.md) |
| Vision & roadmap | [vision.md](docs/vision.md) |
| Components | [architecture.md](docs/architecture.md) |
| Technical reference | [technical-reference.md](docs/technical-reference.md) |
| Codebase audit (Cursor) | [cursor-audit.md](docs/cursor-audit.md) |
| Codebase audit (Codex) | [codex-audit.md](docs/codex-audit.md) |
| Miner | [miner.md](docs/miner.md) |
| Validator | [validator.md](docs/validator.md) |
| Models / APIs | [models.md](docs/models.md) |
| Production / ops | [production.md](docs/production.md) |
| VPS safety / key custody | [vps-safety.md](docs/vps-safety.md) |
| DigitalOcean Droplet runbook | [droplet-operations.md](docs/droplet-operations.md) |
| Service-user migration | [service-user-migration.md](docs/service-user-migration.md) |
| Miner dashboard notes | [miner-dashboard.md](docs/miner-dashboard.md) |
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

## Original Contributors

Spaceτime, Maciej Kula, and Infinitao.
