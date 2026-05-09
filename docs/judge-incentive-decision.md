# Judge Incentive Decision

This note records the current role of the LLM judge in validator rewards. It is
not a claim that judging miner prose is the long-term objective.

## Current Behavior

Validator scoring reaches the judge only after Lean verification passes. The
judge scores the miner's informal reasoning trace on coherence, exploration, and
clarity. The final round score currently blends:

1. `proof_intrinsic_score`, controlled by `LEMMA_SCORE_PROOF_WEIGHT`.
2. The judge rubric composite.

The default `LEMMA_SCORE_PROOF_WEIGHT=0.10` means the judge composite contributes
90 percent of the blend. That makes the judge the dominant live ranking signal
among Lean-valid submissions.

## Problem

Lean pass/fail is objective. The judge rubric is useful, but it is not the Lean
kernel and it is not an economic proof of mathematical value.

Risks:

- Miners can optimize prose for the rubric instead of improving proofs.
- Model/provider changes can shift scores even when proofs are unchanged.
- Prompt hardening reduces obvious injection, but does not make prose judging
  equivalent to formal verification.
- Treating informal explanation quality as permanent would be a product choice,
  not a cleanup detail.

## Decision

Treat the judge as a bootstrap signal by default.

Do not strengthen judge dependence or describe judged reasoning as the permanent
objective unless governance explicitly chooses that product direction. The
objective floor remains Lean verification. The current judge blend may stay as a
practical bootstrap while proof-side metrics, harder problem supply, and
judge-free alternatives are evaluated.

## Go/No-Go Gate

Before making judged informal reasoning a permanent incentive target, decide one
of these paths in a separate scoring commit:

1. **Keep judge as permanent:** explanation quality is part of the subnet's
   product. Then pin the judge stack tightly, publish evaluation examples, and
   keep training export leakage controls current.
2. **Cap judge as bootstrap:** keep the judge low/medium influence while
   collecting proof-side evidence and problem-supply improvements.
3. **Move judge-free:** use Lean/kernel-backed signals, curated challenges,
   container execution, or red/blue evaluation instead of prose judging.

The gate fails if the judge ranking is unstable across provider/model changes,
can be materially improved by prose padding, or conflicts with the stated
one-sentence objective for the subnet.

Minimum evidence for the decision:

1. A fixed evaluation set with Lean-valid submissions covering short traces,
   long but useful traces, polished prose padding, rubric-echo attempts, weak
   reasoning on good proofs, and strong reasoning on equivalent proofs.
2. A judge-stability report across the current pinned judge stack and any
   proposed replacement stack.
3. A comparison against proof-side export data, especially cases where the judge
   likes prose that proof-side metrics or human review consider low value.
4. A short governance note naming the chosen path: permanent judge,
   capped/bootstrap judge, or judge-free.
5. A scoring/profile pin update if the choice changes consensus-critical reward
   behavior.

Do not mix that decision with CLI cleanup, prompt wording cleanup, or unrelated
validator refactors.

## Acceptable Next Changes

- Add offline evaluation fixtures for judge stability and padding attempts.
- Compare judge scores against Lean proof metrics and real validator exports.
- Document any governance choice that makes informal reasoning quality a
  permanent objective.
- Keep live reward changes separate from docs or cleanup commits.

Do not add more prompt-only defenses as the main answer to objective mismatch.
Prompt hardening is useful, but it does not decide what the subnet should reward.

## Decision Record Template

Use this shape for the commit or issue that chooses the next judge path:

```text
Chosen path: permanent judge | capped/bootstrap judge | judge-free

Evidence reviewed:
- Evaluation set:
- Judge stability report:
- Proof-side export report:
- Known failures accepted:

Reward/profile changes:
- Scoring defaults:
- Profile pin fields:
- Migration notes:

Rollback:
- Env/config rollback:
- Operator notice:
```
