# Sybil Economics And Identity

Lemma rewards proofs that pass Lean.

Same-coldkey partitioning stops one coldkey from multiplying rewards through
many hotkeys. It is not sybil resistance.

Machine-readable notes:
[`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml).

## What Lemma Does

| Mechanism | Purpose |
| --- | --- |
| Lean verification gate | Only passing proofs enter scoring. |
| Identical-payload verify reuse | Saves validator CPU for identical proofs. It does not drop reward entries. |
| Same-coldkey partition | Splits one coldkey allocation across its successful hotkeys. |

None of these stop an attacker from registering distinct coldkeys.

## What Lemma Does Not Do

- It does not verify personhood.
- It does not make coldkeys unique humans.
- It does not add a special high-stake miner sampling rule by default.
- It does not make same-coldkey partitioning sybil-proof.

## Where Pressure Comes From

Bittensor subnet UID slots are scarce. Registration cost rises with demand.

That cost is the main economic friction against many identities, not Lemma's
same-coldkey partitioning.

Rough model:

```text
registration_cost ~= expected_reward_per_slot
sybil deterrent ~= cost_of_N_slots > reward_from_N_parallel_miners
```

## Operator Guidance

- Do not call same-coldkey partitioning sybil defense.
- Assume attackers can get many coldkeys when slots are cheap or rewards are
  high.
- Prefer tasks where useful work is the Lean-verified proof, not a subjective
  ranking signal.

## Gate Before Scoring Changes

Do not add another Sybil/Pareto scoring layer without replay evidence.

Minimum evidence:

1. UID registration cost and expected reward per slot.
2. A private `full` export with theorem statements and coldkeys when available.
3. Replay output from:

   ```bash
   uv run python -m tools.sybil_replay_analyze <full-training-export.jsonl> --require-decision-ready
   ```

4. K-miner pressure: one strong miner versus K coordinated miners.
5. Accepted bypasses named clearly.
6. Rollback plan with profile pins and env gates.

If `decision_data_gaps` lists missing rows, epochs, UIDs, theorem ids, or
coldkeys, collect more data instead of changing rewards.

Keep private JSONL private. Public notes should quote summaries, not proofs or
per-miner rows.

## Policy Choices

| Choice | Use when |
| --- | --- |
| Keep current partition | Replay data is weak, or UID cost already matters. |
| Cap or dampen near duplicates | Replays show copied or lightly rewritten work taking too much emission. |
| Winners-take-most | K coordinated miners remain near K-times profitable after current partitioning. |
| Uncopyable work first | The better fix is task design, not another scoring layer. |
| External identity policy | The subnet intentionally wants off-chain identity or stake policy. |

## Decision Record Template

```text
Sybil / Pareto economics decision:
Chosen policy: keep current partition | cap/dampen near duplicates | winners-take-most | uncopyable-work first | no scoring-code change
Decision ready: yes | no
Reason:

Evidence reviewed:
- UID registration cost:
- Expected reward per slot:
- Offline replay dataset:
- Analyzer command:
- Row counts:
- Blockers and gaps:
- Exact clone pressure:
- Rewritten clone pressure:
- Per-epoch notes:
- K-miner result:
- Known bypasses accepted:
- Human review notes:

Reward/profile changes:
- Partition defaults:
- Pareto/scoring changes:
- Profile pin fields:
- Rollout env gates:

Rollback:
- Disable path:
- Operator notice:
- Follow-up review date:
```

## References

- [`lemma/scoring/dedup.py`](../lemma/scoring/dedup.py)
- [`lemma/validator/epoch.py`](../lemma/validator/epoch.py)
- [`tools/sybil_replay_analyze.py`](../tools/sybil_replay_analyze.py)
- [incentive_migration.md](incentive_migration.md)
- [workplan.md](workplan.md)
