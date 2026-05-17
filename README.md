# Lemma

Lemma is a Bittensor subnet for turning open Lean conjectures into verified public proof artifacts.

It publishes formal proof targets, miners submit Lean proof files, validators check them under a pinned Lean and mathlib environment, and verified proofs become eligible for rewards under the subnet rules. After a target is verified and attested, Lemma can publish a canonical proof artifact and prepare an upstream contribution candidate so the result can be reviewed, cited, and linked from the public corpus that supplied the target.

Reward custody is implementation plumbing. The product story is proof production: exact target, Lean proof, validator attestation, reward eligibility, public proof artifact, upstream PR candidate.

## Why Lemma Exists

Mathematics is one of the few AI work domains where correctness can be checked mechanically. A proof is not rewarded because it sounds plausible. It is eligible only when it verifies against the exact published formal statement and policy.

Lemma is being centered on public research-level formal statements from [Formal Conjectures](https://github.com/google-deepmind/formal-conjectures), an open Lean 4 and mathlib repository of formalized conjectures and related statements. Lemma is independent and is not endorsed by Google DeepMind or the Formal Conjectures authors; it uses public statements as target material.

## How The Subnet Works

```text
Formal Conjectures statement
        |
        v
Lemma target registry
        |
        v
Miner Submission.lean
        |
        v
Pinned Lean verification
        |
        v
Validator attestation
        |
        v
Reward eligibility
        |
        v
Canonical proof artifact
        |
        v
Upstream PR candidate
```

Validators check the proof artifact. They do not score informal reasoning, private notes, or prose explanations.

The upstream PR is a publication path, not a payout oracle. Lemma settlement depends on the published target, verifier, and subnet rules. Formal Conjectures maintainers retain normal review authority over their repository.

## Quick Start

Install `uv`, sync the project, and inspect the CLI:

```bash
uv sync
uv run lemma --help
```

Configure local registry, wallet, payout, and verifier settings:

```bash
uv run lemma setup
uv run lemma status
```

List targets:

```bash
uv run lemma mine
```

Inspect or locally verify a target:

```bash
uv run lemma mine <target-id>
uv run lemma mine <target-id> --submission Submission.lean
```

Check validator readiness:

```bash
uv run lemma validate --check
```

## CLI Overview

The visible CLI surface is intentionally small.

| Command | Purpose |
| --- | --- |
| `lemma setup` | Writes target registry, wallet, payout, and Lean verifier settings. |
| `lemma mine` | Lists targets, inspects a target, verifies a proof, and can build reward custody transaction data for live targets. |
| `lemma status` | Prints target registry, custody, and verifier configuration status. |
| `lemma validate` | Checks verifier readiness or runs the optional Lean HTTP worker. |

## Target Registry

The target registry is the source of truth for live work. It contains candidate targets and live reward-backed targets.

- Candidate targets are useful for practice, testing, and review. They are not reward offers.
- Live targets require confirmed reward custody metadata in the registry and matching on-chain custody state.
- Every target fixes a Lean problem payload, target hash, toolchain, submission policy, policy version, and source metadata.

The checked-in starter registry is deliberately a candidate example, not a fake live Formal Conjectures reward.

See [docs/target-registry.md](docs/target-registry.md).

## Formal Conjectures Focus

Formal Conjectures gives Lemma a public source of real mathematical formalization targets. Lemma should pin exact upstream commits and files, preserve source metadata, and clearly distinguish proof-discovery targets from proof-porting targets.

If a Formal Conjectures source row includes `formal_proof` metadata, Lemma treats it as `kind=proof_porting` rather than a normal proof-discovery target.

See [docs/formal-conjectures.md](docs/formal-conjectures.md).

## Verification Model

Proof verification is binary. A submission either passes Lean under the published problem, toolchain, and submission policy, or it fails.

The verifier core lives in:

- `lemma/bounty/`
- `lemma/lean/`
- `lemma/problems/base.py`
- `contracts/LemmaBountyEscrow.sol`

## Docs

- [What is Lemma?](docs/what-is-lemma.md)
- [Formal Conjectures as target supply](docs/formal-conjectures.md)
- [Target registry](docs/target-registry.md)
- [Upstream publication](docs/upstream-publication.md)
- [Proof artifacts](docs/proof-artifacts.md)
- [Submission and publication terms](docs/submission-terms.md)
- [Miner guide](docs/miner.md)
- [Validator guide](docs/validator.md)
- [Rewards](docs/rewards.md)
- [Architecture](docs/architecture.md)
- [Production verification](docs/production.md)
- [Testing](docs/testing.md)
- [FAQ](docs/faq.md)
- [Targets and rewards](docs/bounties.md)

## Development

```bash
uv run ruff check lemma tests
uv run mypy lemma
uv run pytest tests -q
```

## Contracts

```bash
cd contracts
npm install
npm test
npm run compile
```

## Lean Sandbox

```bash
docker build -f compose/lean.Dockerfile -t lemma-lean-sandbox:latest .
LEAN_SANDBOX_IMAGE=lemma-lean-sandbox:latest uv run pytest tests/test_docker_golden.py -v
```

## Security And Operator Notes

Do not publish local environment files, wallets, machine paths, hostnames, private deployment notes, credentials, or local handoff files. Registry and reward metadata should contain only public target and custody information.

## License

Apache-2.0.
