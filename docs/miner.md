# Miner Guide

Miners search for Lean proofs against published Lemma targets.

## 1. Set Up The Repo

```bash
uv sync
uv run lemma setup
uv run lemma status
```

`lemma setup` writes local registry, wallet, payout, and verifier settings into the local environment file.

## 2. List Targets

```bash
uv run lemma mine
```

Live reward-backed targets are shown separately from candidates. Candidates are useful for practice and verifier checks, but they are not reward offers.

## 3. Inspect A Target

```bash
uv run lemma mine <target-id>
```

The CLI prints the registry hash, target hash, source metadata, policy, custody status, and Lean target stub.

## 4. Write `Submission.lean`

Use the printed target stub as the boundary. A typical file looks like:

```lean
import Mathlib

namespace Submission

theorem target_theorem : True := by
  trivial

end Submission
```

The theorem name and type must match the target.

## 5. Verify Locally

```bash
uv run lemma mine <target-id> --submission Submission.lean
```

If Lean accepts the proof under the target policy, the CLI reports that the proof verifies locally.

Accepted proofs for live targets may become public proof artifacts after verification and attestation. Do not include private credentials, private notes, wallet data, local paths, or machine-specific context in `Submission.lean`.

## 6. Build Reward Packages When Applicable

Only live reward-backed targets can build custody packages.

```bash
uv run lemma mine <target-id> \
  --submission Submission.lean \
  --commit \
  --claimant-evm 0x... \
  --payout-evm 0x... \
  --output commit.json
```

For reveal packages:

```bash
uv run lemma mine <target-id> \
  --submission Submission.lean \
  --reveal \
  --claimant-evm 0x... \
  --payout-evm 0x... \
  --salt 0x... \
  --artifact-uri https://... \
  --output reveal.json
```

The CLI builds unsigned transaction data. Inspect it and submit it through normal wallet tooling.

## Publication Expectations

When a target's terms allow publication, a verified and attested proof can be published as a canonical artifact and linked from an upstream PR candidate. Solver attribution should use a public protocol identity or chosen public handle; it should not require private personal information.

See [submission-terms.md](submission-terms.md).

## Common Failure Modes

Unknown target id means the registry does not contain that row.

No confirmed reward custody means the target can still be inspected or locally verified, but it cannot build commit or reveal transaction data.

Lean rejection means the proof did not satisfy the exact target under the published policy.

Docker verification failures usually point to verifier image, cache, or worker configuration rather than proof-search logic.
