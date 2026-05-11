# Lemma

Lemma is a Bittensor subnet for formal math proofs.

Miners submit Lean proof scripts for published theorem statements. Validators
check those scripts with Lean in Docker. If Lean accepts the proof, it can enter
scoring. If Lean rejects it, it cannot.

Terms:

- A theorem is the exact claim to prove.
- A proof script is the Lean code submitted by a miner.
- Lean is the proof checker.
- A miner searches for proofs.
- A validator checks proofs and writes weights.

## Status

Lemma is still early software, but it can run on Bittensor testnet:

- Subnet: `467`
- Network: `test`
- Mainnet name: Finney

Start with [getting-started.md](docs/getting-started.md). The friendlier
operator CLI lives in [lemma-cli](https://github.com/spacetime-tao/lemma-cli).

## What Lemma Produces

Lemma produces verified theorem/proof pairs.

The network publishes a theorem. A miner tries to find a Lean proof. A validator
checks that proof against the theorem. If Lean accepts it, the proof is valid
work.

This is proof mining: Bitcoin miners produce valid hashes; Lemma miners produce
valid Lean proofs.

## Quick Start

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli --extra cli
uv run lemma --help
uv run lemma-cli --help
```

Use one tool: `uv`.

The core repo owns subnet code and dependencies. The `cli` extra installs
`lemma-cli` for setup, doctor checks, and operator help. Use the official
`bittensor-cli` package for the `btcli` command:

```bash
uv sync --extra btcli --extra cli
```

For development, add `--extra dev`.

Use this validator entrypoint:

```bash
uv run lemma validator start
```

Docker images should use:

```dockerfile
ENTRYPOINT ["lemma"]
CMD ["validator", "start"]
```

## Docs

| Topic | File |
| --- | --- |
| First setup | [getting-started.md](docs/getting-started.md) |
| Vision | [vision.md](docs/vision.md) |
| Components | [architecture.md](docs/architecture.md) |
| FAQ | [faq.md](docs/faq.md) |
| Miner | [miner.md](docs/miner.md) |
| Validator | [validator.md](docs/validator.md) |
| Models and APIs | [models.md](docs/models.md) |
| Production | [production.md](docs/production.md) |
| VPS safety | [vps-safety.md](docs/vps-safety.md) |
| Governance and pins | [governance.md](docs/governance.md) |
| Toolchain image policy | [toolchain-image-policy.md](docs/toolchain-image-policy.md) |
| Tests | [testing.md](docs/testing.md) |
| Generated problems | [generated-problems.md](docs/generated-problems.md) |
| Problem supply | [problem-supply-policy.md](docs/problem-supply-policy.md) |
| Catalog sources | [catalog-sources.md](docs/catalog-sources.md) |
| Objective | [objective-decision.md](docs/objective-decision.md) |
| Proof rewards | [proof-verification-incentives.md](docs/proof-verification-incentives.md) |
| Research proof metrics | [proof-intrinsic-decision.md](docs/proof-intrinsic-decision.md) |
| Credibility exponent | [credibility-exponent-decision.md](docs/credibility-exponent-decision.md) |
| Commit-reveal | [commit-reveal.md](docs/commit-reveal.md) |
| Miner verify attest | [miner-verify-attest.md](docs/miner-verify-attest.md) |
| Validator profile attest | [validator-profile-attest.md](docs/validator-profile-attest.md) |
| System requirements | [system-requirements.md](docs/system-requirements.md) |

## References

- [Bittensor](https://docs.learnbittensor.org/)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F) / [miniF2F-lean4](https://github.com/yangky11/miniF2F-lean4)
- [mathlib4](https://github.com/leanprover-community/mathlib4)

## License

Apache-2.0
