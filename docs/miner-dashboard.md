# Miner Dashboard Notes

Lemma does not need a dashboard for consensus. The live reward rule remains
simple: a submitted `proof_script` passes Lean verification or it does not.

A dashboard is still useful for operations. It should help an operator see
whether miners are online, whether the validator is completing rounds, and
whether weights are being set.

## First Version

The first version is intentionally small and read-only:

```bash
uv run python -m tools.ops_dashboard --out ops-dashboard.html
```

It SSHes into the configured Droplets, samples service status, safe `.env`
fields, recent logs, miner ports, Docker status, and the local Lean worker health
endpoint. It writes a static HTML file you can open locally.

Default hosts:

```text
validator / Lean worker: <validator-ssh-host>
miner host:             <miner-ssh-host>
miner ports:            8091,8092,8093,8094,8095,8096
```

Override them when needed:

```bash
uv run python -m tools.ops_dashboard \
  --validator-host <validator-ssh-host> \
  --miner-host <miner-ssh-host> \
  --miner-ports 8091,8092 \
  --out ops-dashboard.html
```

## What It Can Tell You

- Are the Lemma systemd services active?
- Is the deployed git checkout on the expected commit?
- Are miner axon ports reachable?
- Is the local Lean worker health endpoint responding?
- What was the latest sampled `lemma_epoch_summary`?
- Did the sampled logs show `set_weights success=True`?
- What prover timings and proof sizes did miner logs report?

## What It Cannot Tell You

- It cannot prove a miner's latest proof passed just from miner logs. Miners do
  not receive validator proof grades over axon.
- It cannot replace validator logs or chain state.
- It should not expose private training exports or proof text publicly.
- It should not mutate services, wallets, firewall rules, rewards, or scoring.

## Public Dashboard Scope

Do not publish the private ops dashboard. A public dashboard should be generated
from a separate sanitized artifact.

The first public version should show only:

- previous, current, and next generated theorem;
- a plain-English gloss of each theorem statement;
- a short rubric for generated problem types and difficulty labels;
- miner UID;
- public coldkey;
- public hotkey;
- miner score from the public metagraph incentive field;
- unique Lean-verified theorem count in the last 24 hours.
- sortable miner columns.

The theorem triplet is safe to publish for the generated lane because the
problem map is already public and deterministic. The page should still include
the seed metadata it used, so readers can tell which chain head and seed rule
produced the theorem cards.

Generate a local public snapshot with:

```bash
uv run python -m tools.public_dashboard \
  --summary-jsonl /var/lib/lemma/public-summary.jsonl \
  --json-out public-dashboard.json \
  --html-out public-dashboard.html
```

When Lemma moves to a mainnet explorer, pass URL templates so UID, coldkey, and
hotkey cells become links:

```bash
uv run python -m tools.public_dashboard \
  --uid-url-template 'https://<explorer>/subnets/{netuid}/uids/{uid}' \
  --account-url-template 'https://<explorer>/accounts/{address}'
```

Publish only `public-dashboard.json` and `public-dashboard.html`. Do not publish
`ops-dashboard.html`, raw validator logs, `.env` files, wallet files, private
training exports, proof scripts, theorem solutions, Droplet IPs, SSH usernames,
or Lean worker endpoints.

This can be hosted as a static page, for example at `lemmasub.net/dashboard`,
as long as the deployment uploads only the generated public files.

For round-aligned website updates, set the validator to write a public summary
export:

```bash
LEMMA_TRAINING_EXPORT_JSONL=/var/lib/lemma/public-summary.jsonl
LEMMA_TRAINING_EXPORT_PROFILE=summary
```

Then install `deploy/systemd/lemma-public-dashboard.path` and
`deploy/systemd/lemma-public-dashboard.service` on the validator host. The path
unit watches the summary JSONL, so the public dashboard publish job runs after
each validator round writes its summary marker.

## Next Useful Additions

1. Install the public dashboard systemd path/service on the validator host.
2. Upload only the generated public files to static hosting.
3. Add a tiny historical cache only if one-snapshot-at-a-time stops being useful.
