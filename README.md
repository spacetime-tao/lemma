# Lemma

Lemma is a proof formalization subnet. It publishes formal proof targets, checks submissions with Lean, and rewards miners for proofs that pass the exact published statement and policy.

Reward custody is implementation plumbing. The product story is proof correctness: Lean accepts the proof, or it does not.

## CLI

```bash
uv sync
uv run lemma setup
uv run lemma status
uv run lemma mine
uv run lemma mine <target-id> --submission Submission.lean
uv run lemma validate --check
```

Visible commands are intentionally small:

- `lemma setup` writes target registry, wallet, payout, and Lean verifier settings.
- `lemma mine` lists available proof targets, verifies a proof, and can build payout transaction data.
- `lemma status` prints target registry, custody, and verifier configuration status.
- `lemma validate` checks verifier readiness or runs the optional Lean HTTP worker.

## Proof Verification

Lemma keeps proof correctness binary: a submission either passes Lean under the published problem, toolchain, and submission policy, or it does not. Informal reasoning and subjective scoring are not part of the live reward path.

The verifier core lives in:

- `lemma/bounty/`
- `lemma/lean/`
- `lemma/problems/base.py`
- `contracts/LemmaBountyEscrow.sol`

## Docs

- [Proof targets and rewards](docs/bounties.md)
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
