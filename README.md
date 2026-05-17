# Lemma

Lemma is an escrow-backed Lean proof bounty system. A bounty is live only when a registry row points to a funded `LemmaBountyEscrow` bounty. Proofs are checked by Lean; escrow transaction packages are built locally by the CLI.

No funded escrow, no reward promise.

## CLI

```bash
uv sync
uv run lemma setup
uv run lemma status
uv run lemma mine
uv run lemma mine <bounty-id> --submission Submission.lean
uv run lemma validate --check
```

Visible commands are intentionally small:

- `lemma setup` writes bounty, escrow, wallet, and Lean verifier settings.
- `lemma mine` lists escrow-backed bounties, verifies a proof, and builds commit or reveal transaction data.
- `lemma status` prints registry and escrow configuration status.
- `lemma validate` checks verifier readiness or runs the optional Lean HTTP worker.

## Proof Verification

Lemma keeps proof correctness binary: a submission either passes Lean under the published problem, toolchain, and submission policy, or it does not. Informal reasoning and subjective scoring are not part of the live reward path.

The verifier core lives in:

- `lemma/bounty/`
- `lemma/lean/`
- `lemma/problems/base.py`
- `contracts/LemmaBountyEscrow.sol`

## Docs

- [Bounties and escrow](docs/bounties.md)
- [Production verification](docs/production.md)
- [Testing](docs/testing.md)

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
