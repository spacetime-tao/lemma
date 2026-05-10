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

- Audit core Lemma docs and code for cohesion with the binary Lean pass/fail
  subnet design.
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

## Notes For Future Agents

- Preserve binary proof-pass language.
- Keep the reward story binary in docs, tests, and CLI copy.
- Avoid adding defensive complexity where the data model or call path can make
  invalid states impossible.
