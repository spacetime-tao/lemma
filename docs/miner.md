# Miner

The miner is a tiny proof-serving Axon daemon.

It does not run an LLM, retry a prover, score prose, or optimize proof
efficiency. Miners can use any external workflow they want, then submit the
finished Lean file locally.

Browser solve-portal mining has been removed. Miners work offline, use the CLI
to commit from a registered hotkey, and serve the proof through the Axon miner
after reveal opens.

## Guided Mining

```bash
uv run lemma setup --role miner
uv run lemma mine
```

Use `--wallet` and `--hotkey` when one machine has several registered miner
hotkeys:

```bash
uv run lemma setup --role miner --hotkey lemmaminer2
uv run lemma mine --hotkey lemmaminer2
```

`lemma mine` shows the active theorem, asks whether you are ready, verifies the
pasted `Submission.lean`, publishes the commitment, and starts the miner server.
If the proof is already committed, it resumes serving. If commitment failed,
retry with `uv run lemma mine --retry-commit`.

For advanced scripts:

```bash
uv run lemma submit \
  --problem known/smoke/nat_two_plus_two_eq_four \
  --submission path/to/Submission.lean
uv run lemma commit --problem known/smoke/nat_two_plus_two_eq_four
uv run lemma miner start
```

Validators do not answer the mine command directly. Keep the miner running until
your UID appears on `https://lemmasub.net/cadence/`. `lemma target ledger` is
useful only when you have the validator/operator ledger locally. Validators poll
on their own schedule after reveal opens, then run Lean verification; the
default poll interval is about five minutes.
`lemma status` and the public cadence page show the previous, current, and next
theorem in the ordered target window.

Proofs are stored under `LEMMA_MINER_SUBMISSIONS_PATH` or
`~/.lemma/submissions.json`.

## Serve Proofs

```bash
uv run lemma miner start
```

When a validator polls, the miner checks that the requested target id,
statement, imports, Lean toolchain, Mathlib revision, target phase, and stored
commitment match its stored submission. During commit phase it returns no proof.
During reveal phase it returns `proof_script`, the nonce, and the commitment
hash. If anything does not match, it returns no proof.

Once the public cadence page shows your UID for that target, the proof was accepted
and the miner can be stopped unless you want it online for the next target.

## Bounty Proofs

Formal Conjectures bounties are not normal subnet-weight work and do not require
a registered UID. They do require a hotkey signature so the operator can identify
the solver.

```bash
uv run lemma mine --bounty <campaign-id> --submission Submission.lean
```

That command verifies the pinned bounty theorem locally and writes a signed proof
package under `LEMMA_BOUNTY_PACKAGE_DIR` or `~/.lemma/bounty-packages/`.

## Operational Notes

- `AXON_PORT` controls the miner port.
- `AXON_EXTERNAL_IP` should be set explicitly for production miners.
- Miner droplets are optional now; they are proof-serving hosts, not automation
  machines.
- The validator result is not returned over Axon; chain weights are the visible
  reward signal.
- If no current-epoch proof verifies, old winners do not keep getting paid; the
  epoch budget routes to the owner/burn UID.
- Public cadence task data is exported from the cadence source and solved ledger:

```bash
uv run lemma dashboard export --output data/cadence.json
```

The public export shows task state, UIDs, and full hotkeys. It does not publish
proof text, proof hashes, nonces, or commitment hashes.
