# VPS Safety And Key Custody

This guide is for cloud servers running Lemma miners or validators.

## Main Rule

Keep coldkeys local or offline. Put only hotkeys on servers.

- Coldkey: control key. It can transfer TAO, stake, unstake, and replace
  hotkeys.
- Hotkey: service key. A miner or validator can use it on a VPS.

Do not paste seed phrases, passwords, or private key files into chat, logs,
tickets, or shell history.

## Miner VPS

Good default for most operators:

1. Create and fund keys locally.
2. Copy only the miner hotkey to the VPS.
3. Set `AXON_EXTERNAL_IP` to the VPS public IP.
4. Open only the miner axon port, such as `8091`.
5. Run miners under systemd.
6. Keep prover API keys in `.env`, not shell history.

Multiple miner hotkeys can share one VPS for testing. Each needs its own hotkey,
`AXON_PORT`, log file, and service unit.

## Validator VPS

Use a larger host for validators. Lean and Docker need CPU, RAM, and disk.

1. Keep the validator coldkey local.
2. Copy only the validator hotkey to the VPS.
3. Use Docker and a persistent Lean cache.
4. Prefer a long-lived Docker worker.
5. Start from [`deploy/systemd/lemma-validator.service`](../deploy/systemd/lemma-validator.service).
6. Put remote Lean workers on a private network or behind TLS.
7. Set `LEMMA_LEAN_VERIFY_REMOTE_BEARER` for remote workers.

Avoid SSH tunnels for production validation. A tunnel reset can make a good
round look like `verified=0`.

## Separate Lean Worker

Use a separate worker when validator CPU or disk is the bottleneck.

- Same host: bind the worker to `127.0.0.1`.
- Cross-host: use private networking, firewall allowlists, TLS, and bearer auth.
- Monitor worker logs separately from validator logs.

## Test Identities

Use a separate coldkey only when testing separate economic identity.

For throughput tests, multiple hotkeys under one coldkey are enough.

Create wallets locally:

```bash
uv run btcli wallet create --wallet-name codex --hotkey codexhot
```

Fund locally:

```bash
uv run btcli wallet transfer --wallet-name lemma --network test \
  --destination <codex-coldkey-ss58> --amount <test-tao-amount>
```

Register:

```bash
uv run btcli subnets register --wallet-name codex --hotkey codexhot --network test --netuid 467
```

For a validator, stake locally:

```bash
uv run btcli stake add --wallet-name codex --hotkey codexhot --network test --netuid 467
```

After registration, copy only the hotkey files needed by the service.

Codex should not create, store, or hold coldkeys for an operator. It can help
write commands, inspect public chain state, and configure services after the
user creates keys locally.

## Same Proofs And Same Coldkey

If two miners submit the same proof and both pass Lean, both can enter the
weight map.

If those miners share one coldkey, Lemma partitions that coldkey's allocation
across its successful hotkeys. More same-coldkey hotkeys do not multiply the
operator's allocation.

The earlier May 2026 VPS test ran before this rule changed. In that run, UIDs
`2`-`6` passed Lean, but old identical-proof dedup kept UID `2` and dropped the
other identical proofs from rewards.

## Practical Next Steps

1. Keep one-coldkey, multi-hotkey setup for uptime and latency tests.
2. Add a separate coldkey only for economic identity tests.
3. Improve prover diversity for robustness and harder theorem coverage.
4. Run a persistent validator only after Docker cache, hotkey-only custody, and
   monitoring are in place.
