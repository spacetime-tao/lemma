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

- Update core Lemma docs around binary Lean pass/fail rewards.
- Inspect `lemma-cli` and add an in-depth todo list aligned with binary
  proof-pass design.
- Check local and GitHub CI state for Lemma and fix any clear remaining
  failure.
- Run focused verification in both repos and summarize next steps.

## Notes For Future Agents

- Preserve binary proof-pass language.
- Keep the reward story binary in docs, tests, and CLI copy.
- Avoid adding defensive complexity where the data model or call path can make
  invalid states impossible.
