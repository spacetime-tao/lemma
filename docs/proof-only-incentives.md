# Proof-Only Incentive Design

Lemma's long-term reward axis is formal proof quality: miners earn for producing
Lean-valid proofs for published theorem statements, and validators score those
proofs with deterministic proof-side signals.

Informal reasoning can still be useful as optional explanation, training
material, or a human-readable artifact, but it is not part of the permanent
reward function.

## Design Objective

One sentence:

> Lemma rewards valid, efficient Lean proofs.

This keeps the subnet objective close to the thing validators can reproduce:
given a locked theorem statement and a submitted `Submission.lean`, Lean either
accepts the proof or rejects it.

## Reward Shape

1. **Eligibility:** the submitted proof must pass the pinned Lean toolchain,
   Mathlib revision, sandbox policy, theorem binding checks, and cheat scans.
2. **Equivalence:** identical normalized proof payloads are grouped so duplicate
   submissions do not create extra proof work for validators.
3. **Efficiency:** passing proof groups are ranked by deterministic proof-side
   costs, not prose quality.
4. **Weights:** group-level weights are mapped back to eligible miners after
   coldkey / sybil policy is applied.

## Efficiency Signals

Use signals that are deterministic and cheap enough to run inside validator
rounds:

| Signal | Direction | Notes |
| --- | --- | --- |
| Stripped proof text size | Lower is better | Strip comments and blank lines; count the proof body, not unrelated wrapper noise. |
| Proof declaration shape | Lower is usually better | Lean-backed proof metrics such as pretty-printed declaration bytes and delimiter shape are harder to pad than raw text. |
| Verification result | Must pass | Timeouts, compile errors, axioms, and cheat tokens fail eligibility rather than become soft scores. |
| Verification time | Telemetry first | Useful for operations, but hardware-dependent; avoid making it a primary cross-validator reward signal until bounded carefully. |

Knowing the right Mathlib theorem is a valid skill. A short proof that uses the
right existing lemma should score well when the theorem statement is locked and
the imported environment is part of the published challenge.

## What Not To Reward

- Longer prose explanations.
- Rubric-shaped writing.
- Rewriting the theorem in an easier form.
- Comment or whitespace padding.
- Proof scripts that pass only by adding unsound assumptions.
- Extra syntax that does not improve the checked proof.

## Avoiding Proof Golf Traps

Proof-only does not mean raw character-count golf. The first scoring version
should be conservative:

- require Lean pass before any score exists;
- normalize comments and whitespace;
- compare proofs within the same theorem;
- use Pareto-style ranking over proof-side costs instead of one fragile scalar;
- keep proof metrics optional until their runtime cost is acceptable;
- treat problem supply as part of the incentive design.

Some theorems are intentionally solved by recognizing one existing lemma. That is
not a failure. It is only a problem when the live problem supply is too often a
direct restatement of already-known facts.

## Cadence Implications

Proof-only scoring keeps prose-evaluation latency, API cost, prompt-injection
risk, and optional evaluator-profile coordination outside the hot reward path.
It also lets miner
responses be smaller because a proof script is enough for scoring.

That makes 50-block or 25-block theorem windows more plausible, but Lean
verification remains the hard budget. Shorter windows should be adopted only
after warm-cache verification, remote worker throughput, and miner response time
fit the target cadence.

For the current generated v0 lane, 25 blocks is a reasonable target only if the
operator can keep verifier caches warm and bound miner response time. Cold-cache
verification can still consume most of a 5-minute window.

## Implementation Sequence

1. Add a proof-only scoring module that turns verified proof metrics and stripped
   proof text costs into `ScoredEntry` values.
2. Add tests with honest short proofs, honest longer proofs, `simp`/`exact`
   proofs, automation-heavy proofs, comments, strings, unused `have` padding,
   and long-name padding.
3. Run proof-only scoring in shadow mode on live dry-runs and exports.
4. Flip the validator default to proof-only once the tests and shadow data are
   acceptable.
5. Make miner `reasoning_steps` optional and stop rejecting otherwise valid proof
   submissions that omit prose.
6. Remove judge requirements from live validator readiness and profile pins.
7. Move remaining judge/prose tooling to optional research or `lemma-cli` flows.

## Decision Log

| Date | Decision |
| --- | --- |
| 2026-05 | Long-term rewards should be proof-only: Lean-valid proof plus deterministic proof efficiency, with informal reasoning outside the permanent reward axis. |
