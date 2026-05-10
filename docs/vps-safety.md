# VPS Safety And Key Custody

This guide is for operators running Lemma miners or validators on cloud servers.
It keeps the setup simple while avoiding the most common key and uptime mistakes.

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
5. If using a remote Lean worker, keep it on a private network or behind TLS and
   `LEMMA_LEAN_VERIFY_REMOTE_BEARER`.
6. Avoid SSH tunnels for production validator verification. They are fine for
   supervised tests, but one tunnel reset can turn a good miner round into
   `verified=0`.

### Separate Lean Worker VPS

Useful when validator CPU or disk is the bottleneck.

1. Bind the worker to `127.0.0.1` when it is on the same host as the validator.
2. For cross-host workers, use a private VPC, firewall allowlist, TLS, and
   bearer auth.
3. Monitor worker health and logs separately from validator logs.

## Creating A Separate Test Identity

Use a separate coldkey only when you want to test independent economic identity.
For simple throughput testing, multiple hotkeys under one coldkey are enough.

Create the wallet locally:

```bash
uv run btcli wallet create --wallet-name codex --hotkey codexhot
```

Then copy the new coldkey public address and fund it locally:

```bash
uv run btcli wallet transfer --wallet-name lemma --network test \
  --destination <codex-coldkey-ss58> --amount <test-tao-amount>
```

Register the hotkey locally:

```bash
uv run btcli subnets register --wallet-name codex --hotkey codexhot --network test --netuid 467
```

For a validator identity, stake locally from the coldkey:

```bash
uv run btcli stake add --wallet-name codex --hotkey codexhot --network test --netuid 467
```

After registration, copy only the hotkey files needed for the service to the VPS.
Keep the `codex` coldkey seed phrase, coldkey password, and coldkey private file
off the server.

Codex should not create, store, or custody coldkeys for an operator. It can help
write commands, inspect public chain state, and configure services after the user
creates keys and enters passwords locally.

## Why Only One Hotkey Earned In The Test

Two filters are active by default:

1. **Identical proof dedup** applies to everyone. If several UIDs submit the
   same normalized theorem/proof pair, Lemma keeps one scored entry for that
   proof. This prevents exact-copy farming, but it also means simple generated
   theorems with one obvious proof can collapse to one rewarded UID.
2. **Coldkey dedup** applies after that. If several remaining entries share the
   same coldkey, Lemma keeps one entry for that coldkey.

In the May 2026 VPS test, UIDs `2`-`6` all answered successfully, but their
proofs collapsed under identical-proof dedup. UID `2` was the kept entry, so UID
`2` earned alpha and UIDs `3`-`6` did not. The other UIDs did not fail Lean.

## Practical Next Steps

For continued testing:

1. Keep the current one-coldkey, multi-hotkey setup for uptime, latency, and
   observability tests.
2. Add a separate coldkey only when testing independent economic identity.
3. Improve prover diversity before expecting multiple hotkeys to earn on the
   same simple theorem.
4. Run a persistent validator only after the validator host has hotkey-only key
   custody, Docker worker/cache, and monitoring in place.
