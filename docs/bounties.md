# Bounties

Lemma bounties use trustless custody.

A bounty is live only when its reward is funded in `LemmaBountyEscrow` on
Bittensor EVM. Draft registry rows are useful for local verification and UI
work, but they are not reward offers.

## Flow

1. Lemma publishes a pinned theorem record.
2. A sponsor funds the matching escrow bounty on Bittensor EVM.
3. A solver produces a Lean proof by any method.
4. The solver commits on-chain to the hidden artifact hash and payout address.
5. The solver reveals the proof artifact within the reveal window.
6. Validators fetch the artifact, check its hash, run Lean, and attest on-chain.
7. After the challenge window, the escrow contract pays the first valid
   committed proof that met the attestation threshold.

There is no owner-controlled payout path for live bounties. If escrow custody is
not available, the bounty is not live.

## Registry Record

Every live bounty must record:

- `id`
- theorem source, repository, commit, file, and declaration name
- Lean version, Mathlib revision, toolchain id, and policy version
- target statement hash
- escrow contract address, chain id, and escrow bounty id
- funding confirmation derived from chain state, such as `funded: true` or a
  positive `funding_confirmed_block`
- commit, reveal, and challenge windows
- validator attestation threshold

Normal proof bounties must exclude targets that already had a Formal
Conjectures `formal_proof` at bounty creation. Those targets can only be
explicit proof-porting or simplification work.

## Claim Identity

Bittensor SS58 hotkeys and EVM H160 accounts are different key systems. A claim
therefore binds both identities:

- the EVM claimant that submits the escrow transaction;
- the EVM payout address that receives the contract payout;
- the miner hotkey public key;
- a hotkey signature over bounty id, registry hash, artifact hash, commitment
  hash, claimant address, and payout address.

Validators must check that binding before attesting.

## Verification Policy

The default bounty policy is `restricted_helpers`:

- imports must match the registry exactly;
- code must live inside `namespace Submission`;
- helper `def`, `lemma`, and `theorem` declarations are allowed;
- the final theorem must match the exact target theorem and type;
- `sorry`, `admit`, new `axiom` or `constant` declarations, unsafe/native/debug
  hooks, custom syntax/macros/elaborators, notation, attributes, extra imports,
  and target edits are rejected.

The final theorem and helper theorem/lemma declarations are checked for axiom
dependencies. Only the approved Lean/Mathlib baseline is accepted.

## Commands

```bash
uv run lemma status
uv run lemma mine
uv run lemma mine <bounty-id> --submission Submission.lean
uv run lemma mine <bounty-id> --submission Submission.lean --commit \
  --claimant-evm 0x... --payout-evm 0x...
uv run lemma mine <bounty-id> --submission Submission.lean --reveal \
  --claimant-evm 0x... --payout-evm 0x... --salt 0x...
uv run lemma validate --check
```

Advanced compatibility commands such as `lemma bounty ...`, `lemma miner ...`,
and `lemma validator ...` remain available but are no longer the public bounty
path.
