# Lemma

**Lemma is a Bittensor subnet for turning formal mathematics targets
into machine-checked Lean proofs.**

The live work surface has two lanes:

1. Cadence tasks: validators publish one ordered theorem target at a time from
   hybrid curated/generated supply.
2. Miners locally verify a proof, keep it private, and publish an on-chain commitment.
3. After the commit window closes, miners reveal `proof_script` plus the secret nonce.
4. Validators verify the commitment, then verify the Lean file against the locked target.
5. Passing solvers are written to the solved-target ledger.
6. Public cadence data shows task state, UIDs, and full hotkeys, but not proof
   bodies, proof hashes, nonces, or commitment hashes.
7. Current-epoch verified cadence work earns miner weight; unearned weight goes to
   `LEMMA_OWNER_BURN_UID`.
8. Formal Conjectures bounty campaigns are manual owner-emission work: first
   accepted proof wins the listed campaign reward, outside validator weights.

No prose score, proof-efficiency score, difficulty multiplier, subjective judge,
or hidden validator discretion is part of the reward path.

## Current Scope

The public package, command, and docs are `lemma`. The internal Python package is
also `lemma`.

The default cadence problem source is:

```bash
LEMMA_PROBLEM_SOURCE=hybrid
```

Hybrid cadence starts with the curated
[`lemma/problems/known_theorems_manifest.json`](lemma/problems/known_theorems_manifest.json),
then continues into deterministic generated cadence tasks. Formal Conjectures
campaigns live in
[`lemma/formal_conjectures_campaigns.json`](lemma/formal_conjectures_campaigns.json).

## Quick Start

Start from the repo:

```bash
git clone https://github.com/spacetime-tao/lemma.git
cd lemma
uv sync --extra btcli
uv run lemma --help
uv run lemma mine
uv run lemma status
```

`lemma mine` runs a compact preflight before proof entry. It shows wallet,
hotkey, subnet registration, chain/genesis state, and exact `btcli` commands
when something is missing.

Optional local prover tools use OpenAI-compatible provider settings. They are
not required for a manually prepared Lean proof.

```bash
cat >> .env <<'EOF'
LEMMA_PROVER_BASE_URL=https://api.openai.com/v1
LEMMA_PROVER_API_KEY=replace_me
EOF

source .env
curl -sS "$LEMMA_PROVER_BASE_URL/models" \
  -H "Authorization: Bearer $LEMMA_PROVER_API_KEY"

cat >> .env <<'EOF'
LEMMA_PROVER_MODEL=copy_one_model_id_here
EOF
```

Replace the base URL with another OpenAI-compatible provider when needed, then
copy one returned model `id` into `LEMMA_PROVER_MODEL`.

Mine the active target:

```bash
uv run lemma mine
# or choose one registered miner hotkey explicitly
uv run lemma mine --hotkey lemmaminer2
```

`lemma mine` shows the active theorem, asks whether to submit a proof, verifies
the pasted `Submission.lean`, publishes the private commitment, and starts the
miner server. `lemma status` shows the previous, current, and next theorem in
the ordered target window. If a proof is already committed, `lemma mine`
resumes serving.

Run a validator:

```bash
uv run lemma setup --role validator
uv run lemma validate
# or run validation with a separate registered validator hotkey
uv run lemma validate --hotkey lemmaminer2
```

Verify and package a bounty proof:

```bash
uv run lemma mine --bounty <campaign-id> --submission path/to/Submission.lean
```

Advanced/script commands remain callable but are hidden from the main help:

```bash
uv run lemma submit \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
uv run lemma commit --problem known/smoke/nat_two_plus_two_eq_four
uv run lemma miner start
uv run lemma dashboard export --output data/cadence.json
uv run lemma dashboard export-bounties --output data/bounties.json
uv run lemma dashboard publish --output-dir /var/www/lemma-live
uv run lemma bounty-accept --package path/to/bounty-package.json
uv run lemma validator check
uv run lemma validator start
```

Validators must pin both the validator profile hash and the known-theorem
manifest hash before live use:

```bash
uv run lemma meta --raw
```

## Protocol Notes

- The operator-published ledger is the source of truth for solved targets.
- Validators choose the active target as `manifest - solved_ledger`, but a row
  only counts when its theorem statement hash matches the current manifest.
- The first target requires `LEMMA_TARGET_GENESIS_BLOCK`; each next target starts
  at the previous target's accepted block plus one.
- The default commit window is `LEMMA_COMMIT_WINDOW_BLOCKS=25`; validators poll
  for proofs only after reveal opens.
- Public cadence export includes target state, validator hotkey, solver UID, and
  full solver hotkey. It omits proof text, proof hashes, nonces, and commitment
  hashes.
- Targets with known accepted Lean proofs are not launch-eligible.
- Each target row carries a human proof reference, imports, attribution, and
  reviewer duplicate/faithfulness notes.
- Difficulty labels are operator planning metadata, not reward weights.
- Verified cadence work earns `(1 - solve_fraction)^2` of the epoch budget,
  ranked by commitment block. The remaining budget routes to `LEMMA_OWNER_BURN_UID`.
- If nobody solves, the whole epoch routes to `LEMMA_OWNER_BURN_UID`; old solver
  sets do not keep getting paid.
- Duplicate proofs for already-solved targets do not change the ledger.
- The public cadence feed is a tiny JSON export from the cadence source and
  solved ledger. The public bounty feed is a tiny JSON export from the campaign
  registry and acceptance ledger.
- Formal Conjectures tasks are manual owner-emission campaigns: first accepted
  proof wins the campaign ledger, but campaign rows do not affect validator
  `set_weights`. Bounty identity is hotkey-first; a subnet UID is optional.
- Launch on a fresh or intentionally reset subnet state so old Lemma weights do
  not carry into the proof protocol.

See [`docs/protocol.md`](docs/protocol.md) for the compact mechanism reference.

## License

Apache-2.0.

## Original Contributors

Spaceτime, Maciej Kula, and Infinitao.
