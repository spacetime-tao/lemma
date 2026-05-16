# Validator

A Lemma validator sends theorem challenges to miners, verifies submitted Lean
proofs, and publishes weights for eligible work.

Start with [getting-started.md](getting-started.md) if the repo, keys, and
`.env` are not configured yet.

## Validator command map

| Goal | Command |
| --- | --- |
| Configure validator env | `uv run lemma setup --role validator` |
| Check chain, wallet, profile, and Lean readiness | `uv run lemma validator check` |
| Print validator config | `uv run lemma validator config` |
| Rehearse full epochs without `set_weights` | `uv run lemma validator dry-run` |
| Start live validation | `uv run lemma validator start` |
| Run a remote Lean worker | `uv run lemma validator lean-worker` |
| Serve profile hash for peers | `uv run lemma validator profile-attest-serve` |
| Inspect profile hash | `uv run lemma config meta` |

## Setup checklist

1. `uv sync --extra btcli`
2. Create validator wallet keys with `uv run btcli`.
3. Run `uv run lemma setup --role validator`.
4. Register and stake the validator hotkey on the target network/netuid.
5. Build the Lean sandbox image.
6. Run `uv run lemma validator check` until it reports ready.
7. Run `uv run lemma validator dry-run`.
8. Run `uv run lemma validator start`.

For the current public test deployment, use Bittensor testnet subnet 467 unless
a different deployment is explicitly published.

## Lean verification

Validators need Docker or a compatible Lean verification setup. The production
default is Docker with the pinned Lean sandbox image.

```bash
bash scripts/prebuild_lean_image.sh
uv run lemma validator check
uv run lemma validator dry-run
```

For faster steady-state verification, run a long-lived Docker worker and point
Lemma at it with `LEMMA_LEAN_DOCKER_WORKER`. Put the workspace cache on fast
local disk with `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`.

Important verifier docs:

- [toolchain-image-policy.md](toolchain-image-policy.md)
- [validator_lean_load.md](validator_lean_load.md)
- [production.md](production.md)

## Live validation

```bash
uv run lemma validator start
```

Use `dry-run` before live validation when changing host, wallet, verifier,
profile, scoring, or problem-source settings. A passing dry run does not publish
weights; it is the rehearsal path.

Validator rounds follow the published problem-seed windows. Miners submit Lean
proof files, validators verify with the pinned policy, and only Lean-valid work
can become reward-eligible.

## Remote Lean worker

Use a remote worker when the validator host should handle networking and chain
work while another machine handles Lean.

On the worker:

```bash
uv run lemma validator lean-worker --host 0.0.0.0 --port 8787
```

Set `LEMMA_LEAN_VERIFY_REMOTE_BEARER` before binding to non-loopback hosts. On
the validator, set `LEMMA_LEAN_VERIFY_REMOTE_URL` and the same bearer token.

Keep worker ports private or tightly allowlisted. An unauthenticated public Lean
worker is not a safe production setup.

## Profile agreement

Validators should agree on verification and scoring policy. Inspect the local
profile hash with:

```bash
uv run lemma config meta
```

Optional peer attestation uses:

- `LEMMA_VALIDATOR_PROFILE_ATTEST_ENABLED=1`
- `LEMMA_VALIDATOR_PROFILE_ATTEST_PEER_URLS`
- `uv run lemma validator profile-attest-serve --host 0.0.0.0 --port 8799`

This is operator coordination, not a replacement for secure deployment
practices.
