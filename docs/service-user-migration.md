# Migrating Lemma Services Off Root

This note is for Droplets where Lemma is already running under `root` and you
want to move it to a dedicated `lemma` Linux user later.

Do not do this in the middle of live debugging. First confirm the current
validator/miner loop is working, then migrate one Droplet at a time.

## Why Move Off Root?

`root` is the server administrator. A process running as `root` can read and
modify almost anything on the machine.

Lemma can run that way, and it is acceptable for short testnet recovery work, but
it is not the best long-term posture. A normal `lemma` user limits damage if a
service, dependency, or exposed network path behaves badly.

Plainly:

- `root` can control the whole server.
- `lemma` should only operate Lemma files, hotkeys, logs, Docker access, and
  cache directories.
- coldkeys should stay off the Droplet either way.

This is a hardening step, not a reward or proof-mechanism change.

## Safer Order

1. Leave the working root services alone until you have a fresh live round with
   miner responses, validator verification, and `set_weights`.
2. Migrate the miner Droplet first. It is simpler: no Lean Docker cache on the
   hot path unless you enabled local miner verification.
3. Migrate the validator/Lean-worker Droplet second. It needs Docker access and
   correct ownership on `/var/lib/lemma-lean-cache`.
4. Change one Droplet, verify it, then change the next.

## What Changes?

The service files move from root paths:

```ini
WorkingDirectory=/opt/lemma
Environment=PATH=/root/.local/bin:...
ExecStart=/root/.local/bin/uv run lemma miner start
```

to a dedicated service user:

```ini
User=lemma
WorkingDirectory=/opt/lemma
Environment=PATH=/home/lemma/.local/bin:...
ExecStart=/home/lemma/.local/bin/uv run lemma miner start
```

Validator and Lean-worker services use the same idea.

## Migration Checklist

Run commands carefully on one Droplet at a time.

1. Create the user and directories:

```bash
sudo useradd --create-home --shell /bin/bash lemma || true
sudo usermod -aG docker lemma
sudo chown -R lemma:lemma /opt/lemma
sudo install -d -o lemma -g lemma /var/lib/lemma-lean-cache
```

2. Install `uv` for the `lemma` user and sync the repo:

```bash
sudo -iu lemma bash -lc '
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
uv sync --extra btcli
'
```

3. Copy only hotkey files from root to the `lemma` user, if the current wallets
   live under `/root/.bittensor`:

```bash
sudo install -d -o lemma -g lemma /home/lemma/.bittensor
sudo rsync -a /root/.bittensor/wallets/ /home/lemma/.bittensor/wallets/
sudo chown -R lemma:lemma /home/lemma/.bittensor
sudo chmod -R go-rwx /home/lemma/.bittensor/wallets
```

Before doing this, verify the copied wallet tree contains only hotkeys needed by
that Droplet. Do not copy coldkey private files to a server.

4. Make `.env` files readable by the `lemma` user:

```bash
sudo chown lemma:lemma /opt/lemma/.env /opt/lemma/.env.miner* 2>/dev/null || true
sudo chmod 600 /opt/lemma/.env /opt/lemma/.env.miner* 2>/dev/null || true
```

5. Edit each systemd service:

```bash
sudo systemctl edit --full lemma-miner
```

Add `User=lemma`, change `/root/.local/bin/uv` to
`/home/lemma/.local/bin/uv`, and change the `PATH` line to start with
`/home/lemma/.local/bin`.

For the current multi-miner host, repeat for:

```text
lemma-miner
lemma-miner3
lemma-miner4
lemma-miner5
lemma-miner6
lemma-miner7
```

For the validator host, repeat for:

```text
lemma-validator
lemma-lean-worker-http
```

6. Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart <service-name>
sudo systemctl status <service-name> --no-pager
```

7. Verify behavior:

```bash
sudo journalctl -u <service-name> -n 80 --no-pager
```

For miners, confirm each axon port is listening. For the validator, confirm the
Lean worker health check and wait for the next `lemma_epoch_summary`.

## Rollback

If a service fails after migration, use `sudo systemctl edit --full <service>` to
put the root paths back, then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart <service-name>
```

Do not delete the old root wallet or root checkout until the new `lemma` services
have survived live rounds.
