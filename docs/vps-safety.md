# VPS Safety And Key Custody

This guide is for operators running Lemma miners or validators on cloud servers.
It keeps the setup simple while avoiding the most common key and uptime mistakes.
For a DigitalOcean-specific setup and restart walkthrough, see
[droplet-operations.md](droplet-operations.md).
For migrating existing root-run services to a dedicated service user, see
[service-user-migration.md](service-user-migration.md).

## Key Rule

Keep coldkeys local or offline. Put only hotkeys on servers.

- **Coldkey:** treasury/control key. It can transfer TAO, stake, unstake, and
  recover or replace hotkeys. Do not copy the coldkey private file or seed phrase
  to a VPS.
- **Hotkey:** operational key. A miner or validator service can use it on a VPS.
  If the server is compromised, replace the hotkey from the coldkey.

Do not paste seed phrases, coldkey passwords, or private key files into chat,
logs, tickets, or shell history.

## Recommended Layouts

### Miner VPS

Good default for operators.

1. Create and fund/register keys from your local machine.
2. Copy only the miner hotkey to the VPS.
3. Set `AXON_EXTERNAL_IP` explicitly to the VPS public IP.
4. Open only the miner axon port(s), for example `8091`.
5. Run miners under systemd so they restart after reboots.
6. Keep prover API keys in root-readable or service-user-readable `.env` files,
   not in shell history.

Multiple miner hotkeys can share one VPS for testing, but each needs its own
hotkey, `AXON_PORT`, log file, and service unit.

### Validator VPS

Good for persistent operation if the host is large enough.

1. Keep the validator coldkey local.
2. Copy only the validator hotkey to the VPS.
3. Use Docker and a persistent Lean cache directory.
4. Prefer a local long-lived Docker worker on the validator host:
   `LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker`.
5. For systemd, start from
   [`deploy/systemd/lemma-validator.service`](../deploy/systemd/lemma-validator.service)
   and adjust paths only if your checkout or `uv` install differs.
6. If using a remote Lean worker, keep it on a private network or behind TLS and
   `LEMMA_LEAN_VERIFY_REMOTE_BEARER`.
7. Avoid SSH tunnels for production validator verification. They are fine for
   supervised tests, but one tunnel reset can turn a good miner round into
   `verified=0`.

### Separate Lean Worker VPS

Useful when validator CPU or disk is the bottleneck.

1. Bind the worker to `127.0.0.1` when it is on the same host as the validator.
2. For cross-host workers, use a private VPC, firewall allowlist, TLS, and
   bearer auth. `lemma lean-worker` requires bearer auth for non-loopback binds
   unless the dev-only unauthenticated override is set.
3. Monitor worker health and logs separately from validator logs.

## Creating A Separate Test Identity

Use a separate coldkey only when you want to test independent economic identity.
For simple throughput testing, multiple hotkeys under one coldkey are enough.
If you create a second miner hotkey, it can run on the same miner VPS as another
service with its own wallet hotkey, axon port, log file, and systemd unit. Keep
the second coldkey local just like the first one.

Create the wallet locally (replace names with yours):

```bash
uv run btcli wallet create --wallet-name my_remote --hotkey vps_hotkey
```

Then copy the new coldkey public address and fund it locally:

```bash
uv run btcli wallet transfer --wallet-name lemma --network test \
  --destination <my_remote-coldkey-ss58> --amount <test-tao-amount>
```

Register the hotkey locally:

```bash
uv run btcli subnets register --wallet-name my_remote --hotkey vps_hotkey --network test --netuid 467
```

For a validator identity, stake locally from the coldkey:

```bash
uv run btcli stake add --wallet-name my_remote --hotkey vps_hotkey --network test --netuid 467
```

### Copy only the hotkey to the VPS

After registration, the miner or validator on the VPS needs the **hotkey**
signing material, not the coldkey.

1. On the machine where you created the wallet, open your Bittensor wallet
   directory (commonly `~/.bittensor/wallets/<wallet-name>/`).
2. **Never** copy `coldkey`, coldkey seed phrases, or coldkey passwords to the
   VPS.
3. Copy **only** the subtree for this hotkey:
   `.../wallets/<wallet-name>/hotkeys/<hotkey-name>/` (layout can vary slightly
   by `btcli` version; copy the directory that holds **only** that hotkey’s
   files).
4. On the VPS, recreate the same path under `~/.bittensor/wallets/<wallet-name>/`
   and transfer with `scp -r` or `rsync`, for example:

```bash
# From your laptop — replace user, host, wallet, and hotkey names
ssh user@your-vps 'mkdir -p ~/.bittensor/wallets/my_remote/hotkeys'
scp -r ~/.bittensor/wallets/my_remote/hotkeys/vps_hotkey \
  user@your-vps:~/.bittensor/wallets/my_remote/hotkeys/
```

5. Tighten permissions on the VPS (`chmod -R go-rwx ~/.bittensor/wallets` or run
   the service as a dedicated user). Point Lemma / `btcli` at this wallet and
   hotkey name; **hotkey-only** custody is enough for signing miner or validator
   traffic.

Assistants, docs generators, and similar tools should **not** create, store, or
custody coldkeys for an operator. They can help write commands, inspect public
chain state, and configure services after you create keys and enter passwords
locally.

## Same Proofs And Same-Coldkey Hotkeys

Current Lemma rewards every miner entry whose proof verifies. If two miners
submit the same proof for the same theorem and both proofs pass Lean, both can
enter the weight map.

For multiple hotkeys under one coldkey, Lemma partitions that coldkey's
allocation across its successful hotkeys. The operator does not get multiplied
emission by registering more hotkeys under the same coldkey; the allocation is
spread among them.
