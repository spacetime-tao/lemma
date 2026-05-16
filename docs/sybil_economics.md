# Sybil economics and identity (operators)

Lemma scoring rewards proofs that verify in Lean. Same-coldkey partitioning keeps
one operator from multiplying rewards by registering many hotkeys under one
coldkey, but it is not sybil resistance on Bittensor.

Canonical machine-readable notes: [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml).

## What Lemma actually does

| Mechanism | Env | Purpose |
| --- | --- | --- |
| **Lean verification gate** | None | A miner entry is reward-eligible only when its submitted proof verifies against the published theorem. |
| **Difficulty-weighted rolling score** | `LEMMA_SCORING_ROLLING_ALPHA=0.08` | Pass/fail events update a per-UID rolling score; hard and extreme passes lift faster, while easy misses decay faster. |
| **Identical-payload verify reuse** | None | Validators may reuse one Lean verification result for identical payloads inside an epoch. This saves verifier work; it does not drop a miner reward entry. |
| **Same-coldkey partition** | `LEMMA_SCORING_COLDKEY_PARTITION=1` (default on) | After weights are computed, hotkeys sharing one coldkey are capped to one coldkey allocation and that allocation is split among those successful hotkeys. |
| **UID-specific variants** | `LEMMA_UID_VARIANT_PROBLEMS=0` by default | Optional mode where each queried UID receives a deterministic same-split theorem variant, making extra accounts require extra proof work. |

Neither mechanism limits how many **distinct coldkeys** an attacker can register. Creating another coldkey is cheap relative to sybil resistance expectations.

## What does *not* exist here

- **Verified identity** — coldkeys are not proof of personhood.
- **Sybil-proof partitioning** — same-coldkey partitioning is bypassed by **more coldkeys**.
- **Identity proof from UID variants** — variants raise the work cost of many
  accounts, but they do not reveal common ownership.
- **Stake-weighted miner sampling** in the scoring loop beyond what Bittensor’s metagraph already implies for weights — Lemma does not implement an extra “only query high-stake miners” policy by default.

## Where real economic pressure comes from (Bittensor)

Subnet **UID slots are scarce** (typically 256 per subnet). **Registration cost** responds to demand (“UID pressure”). High expected rewards → higher cost to acquire/maintain a slot; that is the primary **economic** friction against spinning up unbounded identities — not Lemma’s same-coldkey partitioning.

Rough equilibrium intuition (from [`sybil.realities.yaml`](../knowledge/sybil.realities.yaml)):

```text
registration_cost ≈ expected_reward_per_slot   (long-run pressure)
sybil deterrent    ≈ cost_of_N_slots > reward_from_running_N_parallel_miners
```

## Design guidance for subnet operators

1. **Do not** treat same-coldkey partitioning as sybil defense; it only prevents one coldkey from multiplying rewards across many hotkeys.
2. **Do** assume attackers can obtain **many coldkeys** if slots are cheap or rewards are high.
3. **Prefer** tasks where the useful work is the proof that verifies, not another subjective ranking signal.
4. **Use** UID-specific variants when copy-across-account pressure matters more
   than shared-theorem comparability.

## Decision gate before Sybil or reward scoring changes

Do not add another sybil or reward scoring layer without replay evidence. The
default code should stay simple: verified proofs become reward-eligible, and
same-coldkey hotkeys share one coldkey allocation.

Minimum evidence:

1. **UID cost context** — current registration cost, expected reward per slot, and whether the subnet is under high or low UID pressure.
2. **Replay data** — at least one offline reward replay comparing the current same-coldkey partition rule with no partition and legacy identical-proof grouping. Start with `uv run python -m tools.sybil_replay_analyze <full-training-export.jsonl> --require-decision-ready` on a private `full` export that includes theorem statements and coldkeys when available.
3. **K-miner pressure** — compare one strong miner against K coordinated miners with copied, lightly rewritten, or complementary outputs.
4. **Accepted bypasses** — explicitly name which attacks remain acceptable for now: distinct coldkeys, semantic trace rewrites, copied proofs with rewritten explanations, or tied scores.
5. **Rollback plan** — any scoring change must be profile-pinned, env-gated for rollout, and easy to disable without changing consensus code.

Read `decision_data_gaps` before arguing policy. If it lists missing replayable
rows, epochs, UIDs, theorem ids, or coldkeys, the right answer is more data, not
a reward change.

Keep the private JSONL export private. The public record can quote the analyzer
summary lines, the chosen policy, and the accepted bypasses without publishing
proof scripts, traces, or per-miner training rows.

Policy choices to make:

| Choice | When it fits | Cost |
| --- | --- | --- |
| **Keep current partition only** | Sybil pressure is theoretical, UID cost is already meaningful, or replay data is inconclusive. | Accepts that distinct-coldkey sybils remain possible. |
| **Cap or dampen near-duplicate reward** | Replays show copied / lightly rewritten work taking too much emission. | Needs a precise similarity rule; easy to overfit. |
| **Winners-take-most by problem subset** | K coordinated miners are consistently close to K× profitable. | Bigger mechanism change; must be simulated before live use. |
| **Uncopyable work lane** | The subnet can generate tasks where extra miners do not cheaply clone the same answer. | Requires problem-supply and validator design, not just scoring. |
| **External identity / governance policy** | The subnet intentionally wants off-chain identity or stake policy. | Outside Lemma’s default open scoring code. |

## Decision rubric

Use this rubric after a private `full` export clears `--require-decision-ready`. If the export does not clear the readiness gate, record **no decision** and collect the fields named in `decision_data_gaps` instead of changing Sybil or reward defaults.

| Decision | Evidence that supports it |
| --- | --- |
| **Keep current partition only** | Same-coldkey hotkeys share one allocation; distinct-coldkey clone pressure is not material relative to UID registration cost. |
| **Cap / dampen near-duplicate reward** | Rewritten clones gain material extra share across several epochs; examples are copied proofs, lightly edited traces, or same-theorem variants; the proposed similarity rule can be replayed before activation. |
| **Move to winners-take-most / stronger subset rewards** | K coordinated miners stay close to Kx group share after current partitioning; current weighting keeps many near-copy entries; a stronger policy can be simulated on the same export before activation. |
| **Invest in uncopyable work / problem supply first** | Replay shows copied outputs are naturally competitive and no simple similarity rule is robust enough; the fix belongs in task design rather than another scoring check. |
| **No scoring-code change** | Coldkeys are missing, the export is too small, UID cost/reward context is unknown, or the finding depends on one hand-picked epoch. |

## Replay summary to preserve

Copy these analyzer lines into the decision record. They are enough to review the
decision later without publishing the private export:

| Line | Why it matters |
| --- | --- |
| `rows_total`, `rows_replayable`, `rows_with_coldkey`, `invalid_json_lines` | Shows whether the export was clean and complete enough to study. |
| `decision_data_blockers`, `decision_data_gaps`, `decision_ready` | Separates "collect more data" from "ready for governance review." |
| `summary_exact_clone_extra_share` | Measures simple copy-paste pressure under the current reward rule. |
| `summary_rewritten_clone_extra_share`, `summary_rewritten_clone_group_share` | Measures lightly rewritten K-miner pressure. |
| Per-epoch `base`, `legacy_identical_dedup`, `no_coldkey_partition`, `legacy_identical_no_partition` lines | Shows whether one epoch is driving the conclusion. |

Decision-record template:

```text
Sybil / reward economics decision:
Chosen policy: keep current partition | cap/dampen near duplicates | winners-take-most | uncopyable-work first | no scoring-code change
Decision ready: yes | no
Reason:

Evidence reviewed:
- UID registration cost:
- Expected reward per slot:
- Offline replay dataset:
- Analyzer command:
- Export profile:
- rows_total / rows_replayable / rows_with_coldkey:
- decision_data_blockers:
- decision_data_gaps:
- summary_exact_clone_extra_share:
- summary_rewritten_clone_extra_share:
- summary_rewritten_clone_group_share:
- Per-epoch notes:
- K-miner result:
- Known bypasses accepted:
- Human review notes:

Reward/profile changes:
- Partition defaults:
- Reward/scoring changes:
- Profile pin fields:
- Rollout env gates:

Rollback:
- Disable path:
- Operator notice:
- Follow-up review date:
```

## References

- Partition implementation: [`lemma/scoring/dedup.py`](../lemma/scoring/dedup.py), used from [`lemma/validator/epoch.py`](../lemma/validator/epoch.py).
- Offline replay helper: [`tools/sybil_replay_analyze.py`](../tools/sybil_replay_analyze.py).
- Incentive overview: [incentive_migration.md](incentive_migration.md), [workplan.md](workplan.md).
