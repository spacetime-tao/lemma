# Agent State

This file is a lightweight handoff note for long-running agent work. Keep it
short, current, and useful when chat context is lost.

## Working Mentality

Treat every line of code as a liability. Every line must be maintained,
reviewed, tested, and understood. Prefer lean changes that fix the underlying
shape of the system over extra layers of checks, guards, or compensating
logic.

## Current Direction

Lemma's live incentive mechanism should center on a binary outcome: a miner
either submits a Lean proof for the theorem that passes verification, or it
does not.

Reason: the product center is simple, reproducible proof acceptance.

## Active Checklist

- Audit core Lemma docs and code for cohesion with the proof-verification subnet
  design.
- Keep `lemma-cli` and core Lemma aligned so operator setup feels like one
  simple path, not two overlapping tools.
- Continue VPS deployment testing:
  - miner hotkeys on one droplet or several droplets;
  - validator on a separate droplet;
  - local machine mainly for development and key safety unless tests prove
    local operation is better.
- Measure whether the current VPS setup can reliably earn alpha:
  - miner forward response time;
  - prover API latency and timeout behavior;
  - validator Lean verification time, cold and warm;
  - scored miner count per validator round;
  - timeout/fail reasons from validator logs.
- Speed up the hot path where real timings justify it:
  - persistent `LEMMA_LEAN_VERIFY_WORKSPACE_CACHE_DIR`;
  - long-lived `LEMMA_LEAN_DOCKER_WORKER`;
  - remote Lean worker on Linux if validator CPU or disk becomes the bottleneck;
  - prover retry/timeout/model tuning only when it improves forward completion.
- Use tests and real logs before changing mechanism code.

## Relevant Docs

- Binary reward design: `docs/objective-decision.md`,
  `docs/proof-only-incentives.md`, `docs/faq.md`.
- VPS/operator guidance: `docs/production.md`, `docs/system-requirements.md`,
  `docs/miner.md`, `docs/validator.md`.
- Validator throughput: `docs/validator_lean_load.md`, `docs/workplan.md`.
- CLI/core install cohesion: `README.md`, `docs/getting-started.md`,
  sibling repo `lemma-cli/README.md`.

## Testing Notes To Preserve

- Test one miner hotkey first, then add more hotkeys only after the single-hotkey
  path is stable.
- Multiple miner hotkeys on one VPS need separate wallet hotkeys, axon ports,
  logs, and service units.
- Validator tests should compare cold verification against warmed verification;
  do not use the cold Mathlib path as the steady-state estimate.
- Docker Desktop on a local Mac can mislead verification timing because bind
  mounts and filesystem caching behave differently than Linux VPS storage.
- The practical goal is not only local PASS. The goal is miners and validators
  staying online, responding inside the validator forward window, verifying
  proofs, setting weights, and earning alpha.

## Latest Baseline Status

- Core Lemma `main` pushed through `bd8f271`
  (`Clarify proof-verification messaging`).
- `lemma-cli` `main` pushed through `022a779` (CLI proof-verification
  messaging).
- Local verification before VPS testing:
  - core `uv run pytest`: 250 passed, 2 skipped;
  - core `uv run ruff check lemma tests`: passed;
  - CLI pytest: 27 passed;
  - CLI ruff: passed;
  - `lemma-cli doctor`: passed;
  - `lemma validator-check`: printed READY after subnet pins refresh.
- Worker droplet `lemma-lean-worker-1` (`167.99.145.132`):
  - repo `/opt/lemma` updated to `bd8f271`, `uv sync` run, service restarted;
  - `lemma-lean-worker-http.service` active;
  - worker listens on `127.0.0.1:8787`; remote external port refused, which is
    expected for the private worker;
  - local worker health on the droplet returned `{"status":"ok"}`.
- Miner droplet `lemma-miner-1` (`161.35.50.115`):
  - repo `/opt/lemma` updated to `bd8f271`, `uv sync --extra btcli` run;
  - active miner services on ports `8091`-`8095`, externally reachable;
  - UIDs `2`-`6` registered on testnet netuid `467` at that IP/port set;
  - metagraph snapshot around block `7091614` still showed zero incentive,
    consensus, and emission for UIDs `2`-`6`.
- Direct validator dry-run through an SSH tunnel to the worker:
  - theorem `gen/7091600`;
  - `verified=5`, `scored=5`, `dedup_dropped=4`, `seconds=68.11`;
  - dry-run weights subset: `{2: 1.0}`;
  - all five miners solved the same theorem in roughly `13.6`-`16.1` seconds;
  - this did not set weights or earn alpha because it was a dry-run.
- One live validator epoch ran locally through an SSH tunnel to the worker:
  - theorem `gen/7091700`;
  - `verified=5`, `scored=5`, `dedup_dropped=3`, `coldkey_dropped=1`,
    `seconds=309.83`;
  - live weights subset: `{2: 1.0}`;
  - `set_weights success=True message=Not waiting for finalization or inclusion`;
  - miner logs show UIDs `2`-`6` answered in roughly `13.6`-`19.0` seconds.
- Current alpha blocker: local validator UID `1` has `stake=0.0` and
  `validator_permit=False`. Its `last_update` moved to block `7091764`, but raw
  chain weights still only show UID `0` as a visible validator row. To make miner
  hotkeys earn alpha from this validator, stake testnet TAO to the validator
  hotkey and confirm it receives validator permit, then run another live epoch.
- Staking attempt from Codex was blocked by the encrypted coldkey password
  prompt. No stake moved; wallet `lemma` remained at `2.272251606` free and
  `0.0` staked. User needs to run the stake command locally and enter the
  coldkey password outside chat.
- User completed staking locally after increasing slippage tolerance. Wallet
  `lemma` then showed `0.268630335` free and `2.214305457` staked; metagraph at
  block `7092853` showed validator UID `1` with `S=2277.37988281`, `active=1`,
  and `validator_permit=False`. A follow-up live epoch was started to see if the
  now-staked validator can write a visible weight row and move miner alpha.
- Post-stake immediate live epoch:
  - remote-worker attempt at theorem `gen/7093100` failed verification because
    the local SSH tunnel to the worker reset; miners still answered in roughly
    `21.9`-`34.7` seconds.
  - local Docker-worker retry at theorem `gen/7093200` succeeded:
    `verified=5`, `scored=5`, `dedup_dropped=4`, `seconds=258.73`,
    live weights subset `{2: 1.0}`, `set_weights success=True`.
  - metagraph at block `7093239` showed UID `1` with `validator_permit=True`,
    `S=2297.36254883`, and validator emission `13.71050453`.
  - miner UIDs `2`-`6` still showed zero immediate emission because subnet
    `commit_reveal_weights_enabled=True`; UID `1` has a timelocked weight commit
    from block `7093234`, reveal period `1` epoch, and `revealed_uid1=None`.
    Check again after the next epoch/reveal window.
- After the next epoch/reveal window, metagraph at block `7093921` showed miner
  alpha moving:
  - raw weights rows: UID `0 -> 1`, UID `1 -> 2`;
  - validator UID `1`: `validator_trust=1.0`, `emission=148.01081848`,
    `S=2528.13598633`;
  - miner UID `2`: `consensus=1.0`, `incentive=1.0`,
    `emission=148.01081848`, `S=148.01081848`;
  - miner UIDs `3`-`6` remained at zero because the validator round deduped
    identical proof submissions and kept UID `2`.

## Notes For Future Agents

- Preserve proof-verification language.
- Keep the reward story binary in docs, tests, and CLI copy.
- Avoid adding defensive complexity where the data model or call path can make
  invalid states impossible.
