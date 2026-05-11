# Validator

A validator sends theorem challenges to miners, checks returned proofs with
Lean, scores passing proofs, and writes weights.

Use Docker for production validation.

## Quick Path

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma-cli rehearsal
uv run lemma validator-check
uv run lemma validator start
```

Use `uv run lemma validator start` from the repo root.

Validators wait for subnet epoch boundaries. There is no timer-only mode.

## Proof Rule

Submitted proofs must pass Lean for the published theorem before they can enter
scoring.

The live rule is simple:

- Lean passes: the proof can enter scoring.
- Lean fails: the proof cannot receive proof score.

## Docker

Docker Engine or Docker Desktop must be installed and running when
`LEMMA_USE_DOCKER=1`.

`lemma validator start` refuses to run with `LEMMA_USE_DOCKER=false`. Local tools
may allow host Lean for debugging, but production validators should use the
pinned sandbox image.

## Fast Local Docker Verify

Use a persistent Lean cache:

```bash
mkdir -p /var/lib/lemma-lean-cache
```

Start a long-lived worker:

```bash
bash scripts/start_lean_docker_worker.sh
```

Set the worker URL:

```bash
LEMMA_LEAN_DOCKER_WORKER=http://127.0.0.1:8787
```

This avoids starting a fresh container for every proof.

## Host Lean

Host Lean is for local debugging only:

```bash
LEMMA_USE_DOCKER=false
LEMMA_ALLOW_HOST_LEAN=1
```

The host toolchain must match the pinned sandbox. Check subnet policy before
using host Lean outside local tests.

## macOS Note

Docker Desktop on macOS can be much slower than Linux. Use Linux with local SSD
for production timing.

## Remote Lean Worker

To move Lean work off the validator host, run:

```bash
uv run lemma lean-worker --host 0.0.0.0 --port 8787
```

On the validator, set:

```bash
LEMMA_LEAN_VERIFY_REMOTE_URL=http://<worker>:8787
```

If the network is not private, also set `LEMMA_LEAN_VERIFY_REMOTE_BEARER`.

More load guidance: [validator_lean_load.md](validator_lean_load.md).

## Useful Commands

| Need | Command |
| --- | --- |
| Prover plus Lean preview | `uv run lemma-cli rehearsal` |
| Prover only | `uv run lemma-cli try-prover` |
| Prover plus local Lean | `uv run lemma-cli try-prover --verify` |
| Full validator without weights | `uv run lemma validator dry-run` |
| Readiness check | `uv run lemma validator-check` |
| Start validator | `uv run lemma validator start` |
| Print validator config | `uv run lemma-cli validator-config` |

## Validator Profile Attest

Validators should run the same scoring and verification profile.

When `LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED=1`, startup checks each URL in
`LEMMA_VALIDATOR_PROFILE_ATTEST_PEER_URLS`. Each peer should return the same
`validator_profile_sha256`.

Serve your own hash with:

```bash
uv run lemma validator profile-attest-serve --host 0.0.0.0 --port 8799
```

This is an operator check, not transport security. See
[validator-profile-attest.md](validator-profile-attest.md).

## Docker Compose

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml up validator
```

More production notes: [production.md](production.md).
