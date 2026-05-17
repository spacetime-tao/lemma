# Architecture

Lemma has four main pieces:

- target registry,
- miner CLI,
- Lean verifier,
- reward custody helpers,
- optional publication sidecar.

## Data Flow

```text
Registry JSON
    |
    v
Miner CLI
    |
    v
Submission.lean
    |
    v
Lean verifier
    |
    v
Verification result
    |
    v
Reward custody package for live targets
    |
    v
Proof artifact and upstream PR package
```

## Target Registry

The registry is public JSON. It describes candidate and live targets. Live targets add confirmed custody metadata; candidates do not.

## Problem Abstraction

`lemma/problems/base.py` defines the proof target shape. `lemma/lean/problem_codec.py` turns registry payloads into verifier-ready problems.

## Verification Boundary

`lemma/lean/` materializes the workspace, applies submission policy checks, and runs Lean either through Docker, host Lean for debugging, or the optional HTTP worker.

## Miner CLI

`lemma/cli/main.py` keeps the public command surface small:

- `setup`
- `mine`
- `status`
- `validate`

The CLI can list targets, inspect a target, verify a local proof, and build custody packages for live targets.

## Reward Custody

`lemma/bounty/escrow.py` and `contracts/LemmaBountyEscrow.sol` keep reward custody separate from proof correctness. The verifier decides whether the proof passes; custody handles commit, reveal, attestation, and resolution mechanics.

## Publication Sidecar

Publication is intentionally downstream of verification and custody. A sidecar can re-run or confirm verification, assemble a canonical proof artifact, and prepare a Formal Conjectures PR package for human review.

This pass documents the sidecar shape only. It does not add a GitHub bot, artifact host, runtime module, or CLI command.

## Why Custody Is Separate

Candidate targets should be useful before money is attached. Live reward claims need stronger metadata and chain state. Keeping those concerns separate avoids implying rewards where none are confirmed.
