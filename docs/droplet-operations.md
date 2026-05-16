# DigitalOcean Droplet Operator Runbook

This runbook is for bringing Lemma miners, validators, and optional Lean workers
back online on DigitalOcean Droplets. It assumes testnet `netuid 467` unless your
subnet operator has published a different network, netuid, and validator profile.

Use this together with [getting-started.md](getting-started.md),
[vps-safety.md](vps-safety.md), [miner.md](miner.md), and
[validator.md](validator.md). If you already have root-run services and want to
migrate them later, see [service-user-migration.md](service-user-migration.md).

## Local Or Droplets?

Use your local machine for key creation, coldkey custody, registration, staking,
and code review.

Use Droplets for live miner and validator operation when you want realistic
networking and do not want to run Docker locally. That is the better default for
the current live-evidence work: miners get a stable public IP and validators run
Docker/Lean on Linux instead of depending on Docker Desktop or a blocked local
Docker socket.

Do not treat a Droplet as safer than your laptop for secrets. A Droplet is just a
server on the internet. Put only hotkeys on it.

## Recommended Layout

| Place | Runs | Key material |
| --- | --- | --- |
| Local machine | `btcli` funding, registration, staking, reviews | Coldkeys and hotkeys before copying |
| Miner Droplet | `lemma miner start` | Miner hotkey only |
| Validator Droplet | `lemma validator start`, Docker, Lean cache | Validator hotkey only |
| Optional Lean Droplet | `lemma lean-worker` | No wallet keys required |

Start with one miner hotkey and one validator. Add more miner hotkeys only after
the single-hotkey path stays online and answers inside the validator window.

## What Agents Can Safely Help With

Tools like Codex can help draft commands, inspect public chain state, review
logs, edit docs, and configure systemd services.

Use caution around custody and live operations:

- Do not paste seed phrases, coldkey passwords, private key files, API keys, or
  bearer tokens into chat.
- Do not let an assistant create or hold your coldkey.
- Do not approve a command that transfers funds, stakes, unstakes, deletes a
  wallet, destroys a Droplet, or opens broad firewall access unless you
  understand the exact effect.
- Prefer asking an assistant to explain a command before you run it.

## Droplet And Firewall Setup

Create Ubuntu Droplets with SSH-key login. DigitalOcean describes Droplets as
Linux VMs and supports SSH keys during creation. Use DigitalOcean Cloud Firewalls
or an equivalent host firewall before exposing services.

Minimum inbound rules:

| Role | Inbound rules |
| --- | --- |
| Miner | SSH from your IP; miner `AXON_PORT` from the public internet so validators can reach it |
| Validator | SSH from your IP; optional profile-attest port only from peers you trust |
| Lean worker | SSH from your IP; worker port only from the validator private IP or private VPC |

Keep outbound traffic open unless you have a stricter network policy ready.
Validators and miners need chain RPC, package installs, prover APIs, and git or
container registry access.

For a cross-host Lean worker, do not expose unauthenticated `0.0.0.0:8787` to the
public internet. Use private networking or a tight firewall allowlist, and set
matching `LEMMA_LEAN_VERIFY_REMOTE_BEARER` on the validator and worker.

DigitalOcean references:

- [Getting started with Droplets](https://docs.digitalocean.com/products/droplets/getting-started/)
- [Getting started with Cloud Firewalls](https://docs.digitalocean.com/products/networking/firewalls/getting-started/)
- [Create a Cloud Firewall](https://docs.digitalocean.com/products/networking/firewalls/how-to/create/)

## Server Bootstrap

Run this once per Droplet as the initial SSH user. It creates a dedicated
`lemma` service user and keeps the checkout under `/opt/lemma`.

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates build-essential docker.io
sudo systemctl enable --now docker

sudo useradd --create-home --shell /bin/bash lemma || true
sudo usermod -aG docker lemma
sudo install -d -o lemma -g lemma /opt/lemma
sudo install -d -o lemma -g lemma /var/lib/lemma-lean-cache
```

Open a shell as the service user:

```bash
sudo -iu lemma bash -lc '
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH=/home/lemma/.local/bin:$PATH
git clone https://github.com/spacetime-tao/lemma.git /opt/lemma
cd /opt/lemma
uv sync --extra btcli
'
```

If the repo already exists, update instead:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
git pull --ff-only
uv sync --extra btcli
'
```

## Keys And Registration

Create, fund, register, and stake from your local machine. Copy only the hotkey
directory to the Droplet. The coldkey private file and seed phrase stay local.

See the hotkey-only copy checklist in [vps-safety.md](vps-safety.md#copy-only-the-hotkey-to-the-vps).

After copying the hotkey, tighten permissions on the Droplet:

```bash
sudo -iu lemma bash -lc 'chmod -R go-rwx ~/.bittensor/wallets'
```

## Miner Droplet

Configure from the repo root:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
uv run lemma setup --role miner
uv run lemma doctor
uv run lemma status
uv run lemma miner dry-run
'
```

Important miner `.env` values:

```bash
SUBTENSOR_NETWORK=test
NETUID=467
BT_WALLET_COLD=<wallet-name>
BT_WALLET_HOT=<miner-hotkey-name>
AXON_EXTERNAL_IP=<miner-droplet-public-ip>
AXON_PORT=8091
LEMMA_MINER_FORWARD_TIMELINE=1
```

Install a systemd unit:

```bash
sudo tee /etc/systemd/system/lemma-miner.service >/dev/null <<'EOF'
[Unit]
Description=Lemma miner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=lemma
WorkingDirectory=/opt/lemma
Environment=PATH=/home/lemma/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/lemma/.local/bin/uv run lemma miner start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now lemma-miner
sudo journalctl -u lemma-miner -f
```

For multiple miners on one Droplet, the lowest-surprise setup is one working
directory per hotkey, each with its own `.env`, `AXON_PORT`, log stream, and
systemd unit. Lemma's `.env` normally wins over process environment variables, so
do not rely on systemd `Environment=` overrides unless you also set
`LEMMA_PREFER_PROCESS_ENV=1` intentionally.

## Validator Droplet

Configure and check readiness:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
uv run lemma setup --role validator
uv run lemma validator check
'
```

Important validator `.env` values:

```bash
SUBTENSOR_NETWORK=test
NETUID=467
BT_VALIDATOR_WALLET_COLD=<wallet-name>
BT_VALIDATOR_WALLET_HOT=<validator-hotkey-name>
LEAN_SANDBOX_IMAGE=lemma/lean-sandbox:latest
LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=/var/lib/lemma-lean-cache
LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS=8
LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES=17179869184
LEMMA_VALIDATOR_MIN_FREE_BYTES=1073741824
LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker
LEMMA_LEAN_VERIFY_TIMING=1
```

For production, replace `lemma/lean-sandbox:latest` with the subnet-published
immutable image ref.

Build the local sandbox image if you are using the local default:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
bash scripts/prebuild_lean_image.sh
./scripts/start_lean_docker_worker.sh --update-dotenv
uv run lemma preview
uv run lemma validator check
'
```

Install a systemd unit:

```bash
sudo tee /etc/systemd/system/lemma-validator.service >/dev/null <<'EOF'
[Unit]
Description=Lemma validator
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Type=simple
User=lemma
WorkingDirectory=/opt/lemma
Environment=PATH=/home/lemma/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/lemma/.local/bin/uv run lemma validator start
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now lemma-validator
sudo journalctl -u lemma-validator -f
```

Watch for `lemma_epoch_summary`. The live target is not merely a local pass; it
is miner forwards completing, Lean verification finishing, nonzero scored miners,
`set_weights`, and emissions moving across repeated rounds.

## Optional Separate Lean Worker Droplet

Use a separate worker only when validator CPU, disk, or Docker startup becomes
the bottleneck. The worker needs the same code checkout, `.env` verifier pins,
Docker image, and cache setup, but it does not need wallet keys.

Worker `.env`:

```bash
LEAN_SANDBOX_IMAGE=<same-image-ref-as-validator>
LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR=/var/lib/lemma-lean-cache
LEMMA_LEAN_WORKSPACE_CACHE_MAX_DIRS=8
LEMMA_LEAN_WORKSPACE_CACHE_MAX_BYTES=17179869184
LEMMA_LEAN_DOCKER_WORKER=lemma-lean-worker
LEMMA_LEAN_VERIFY_REMOTE_BEARER=<long-random-token>
```

Start the worker:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
uv sync --extra btcli
bash scripts/prebuild_lean_image.sh
./scripts/start_lean_docker_worker.sh --update-dotenv
uv run lemma lean-worker --host 0.0.0.0 --port 8787
'
```

On the validator:

```bash
LEMMA_LEAN_VERIFY_REMOTE_URL=http://<worker-private-ip>:8787
LEMMA_LEAN_VERIFY_REMOTE_BEARER=<same-long-random-token>
```

Keep the worker port private or tightly allowlisted to the validator. The worker
refuses unauthenticated non-loopback binds by default; do not use the dev-only
override for live operation.

For persistent operation, put the worker under systemd too:

```bash
sudo tee /etc/systemd/system/lemma-lean-worker.service >/dev/null <<'EOF'
[Unit]
Description=Lemma Lean verify worker
After=network-online.target docker.service
Wants=network-online.target docker.service

[Service]
Type=simple
User=lemma
WorkingDirectory=/opt/lemma
Environment=PATH=/home/lemma/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/lemma/.local/bin/uv run lemma lean-worker --host 0.0.0.0 --port 8787
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now lemma-lean-worker
sudo journalctl -u lemma-lean-worker -f
```

## Re-Spin Checklist

Use this when restarting existing Droplets:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
git status --short --branch
git pull --ff-only
uv sync --extra btcli
uv run lemma doctor
uv run lemma status
'
```

Miner:

```bash
sudo systemctl restart lemma-miner
sudo journalctl -u lemma-miner -n 100 --no-pager
```

Validator:

```bash
sudo -iu lemma bash -lc '
export PATH=/home/lemma/.local/bin:$PATH
cd /opt/lemma
uv run lemma validator check
'
sudo systemctl restart lemma-validator
sudo journalctl -u lemma-validator -n 100 --no-pager
```

Record after each run:

- commit SHA and `uv run lemma meta`;
- Droplet size, region, public IP, and private IP if used;
- `.env` pins without secrets;
- miner forward latency and prover timeout/retry reasons;
- validator Lean cold/warm timing and failure reasons;
- scored miner count, `set_weights`, and emission movement.
