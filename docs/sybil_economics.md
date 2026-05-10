# Sybil economics and identity (operators)

Lemma scoring includes **deduplication** knobs that reduce certain multi-account games — they are **not** a substitute for sybil resistance on Bittensor.

Canonical machine-readable notes: [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml).

## What Lemma actually does

| Mechanism | Env | Purpose |
| --- | --- | --- |
| **Identical submission dedup** | `LEMMA_SCORING_DEDUP_IDENTICAL` (default on) | Same normalized `(theorem_statement, proof_script)` fingerprint → keep **best** score only ([`dedup.py`](../lemma/scoring/dedup.py)). Proof comments are stripped and whitespace is collapsed. Reduces copy-paste clutter in one epoch. |
| **Coldkey dedup** | `LEMMA_SCORING_COLDKEY_DEDUP` (default on) | Among UIDs on the metagraph, **one entry per coldkey string** — keep best score ([`dedup_coldkeys`](../lemma/scoring/dedup.py)). Reduces **same-coldkey multi-hotkey** farming in a round. |

Neither mechanism limits how many **distinct coldkeys** an attacker can register. Creating another coldkey is cheap relative to sybil resistance expectations.

## What does *not* exist here

- **Verified identity** — coldkeys are not proof of personhood.
- **Sybil-proof dedup** — “one hotkey per coldkey” is bypassed by **more coldkeys**.
- **Stake-weighted miner sampling** in the scoring loop beyond what Bittensor’s metagraph already implies for weights — Lemma does not implement an extra “only query high-stake miners” policy by default.

## Where real economic pressure comes from (Bittensor)

Subnet **UID slots are scarce** (typically 256 per subnet). **Registration cost** responds to demand (“UID pressure”). High expected rewards → higher cost to acquire/maintain a slot; that is the primary **economic** friction against spinning up unbounded identities — not Lemma’s coldkey dedup.

Rough equilibrium intuition (from [`sybil.realities.yaml`](../knowledge/sybil.realities.yaml)):

```text
registration_cost ≈ expected_reward_per_slot   (long-run pressure)
sybil deterrent    ≈ cost_of_N_slots > reward_from_running_N_parallel_miners
```

## Design guidance for subnet operators

1. **Do not** treat coldkey dedup as sybil defense — treat it as **anti-clutter** for same-coldkey multi-hotkey behavior.
2. **Do** assume attackers can obtain **many coldkeys** if slots are cheap or rewards are high.
3. **Prefer** mechanism design where **running K independent miners** is **not** ~K× as attractive as one good miner (e.g. diminishing returns, uncopyable work, rate limits via economics rather than identity).
4. **Optional policy knobs** (not enforced by this doc — subnet governance): tie-break rules when scores tie, registration burns, emissions caps per coldkey family, off-chain KYC — those are **outside** Lemma’s default codebase unless you add them explicitly.

## Decision gate before Sybil/Pareto scoring changes

Do not add another sybil/Pareto scoring layer until the subnet has answered this gate. The default code should stay simple until there is evidence that a specific policy beats the current anti-clutter dedup rules.

Minimum evidence:

1. **UID cost context** — current registration cost, expected reward per slot, and whether the subnet is under high or low UID pressure.
2. **Replay data** — at least one offline reward replay with identical-submission dedup on/off and coldkey dedup on/off. Start with `uv run python -m tools.sybil_replay_analyze <full-training-export.jsonl> --require-decision-ready` on a private `full` export that includes theorem statements and coldkeys when available.
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
| **Keep current dedup only** | Sybil pressure is theoretical, UID cost is already meaningful, or replay data is inconclusive. | Accepts that coldkey sybils remain possible. |
| **Cap or dampen near-duplicate reward** | Replays show copied / lightly rewritten work taking too much emission. | Needs a precise similarity rule; easy to overfit. |
| **Winners-take-most by problem subset** | K coordinated miners are consistently close to K× profitable. | Bigger mechanism change; must be simulated before live use. |
| **Uncopyable work lane** | The subnet can generate tasks where extra miners do not cheaply clone the same answer. | Requires problem-supply and validator design, not just scoring. |
| **External identity / governance policy** | The subnet intentionally wants off-chain identity or stake policy. | Outside Lemma’s default open scoring code. |

## Decision rubric

Use this rubric after a private `full` export clears `--require-decision-ready`. If the export does not clear the readiness gate, record **no decision** and collect the fields named in `decision_data_gaps` instead of changing Sybil/Pareto defaults.

| Decision | Evidence that supports it |
| --- | --- |
| **Keep current dedup only** | Exact clones gain little or no extra share; rewritten clones do not gain durable extra share across epochs; UID registration cost is already meaningful relative to expected reward. |
| **Cap / dampen near-duplicate reward** | Rewritten clones gain material extra share across several epochs; examples are copied proofs, lightly edited traces, or same-theorem variants; the proposed similarity rule can be replayed before activation. |
| **Move to winners-take-most / stronger subset rewards** | K coordinated miners stay close to Kx group share after current dedup; Pareto ranking keeps many near-copy entries; a stronger policy can be simulated on the same export before activation. |
| **Invest in uncopyable work / problem supply first** | Replay shows copied outputs are naturally competitive and no simple similarity rule is robust enough; the fix belongs in task design rather than another scoring check. |
| **No scoring-code change** | Coldkeys are missing, the export is too small, UID cost/reward context is unknown, or the finding depends on one hand-picked epoch. |

## Replay summary to preserve

Copy these analyzer lines into the decision record. They are enough to review the
decision later without publishing the private export:

| Line | Why it matters |
| --- | --- |
| `rows_total`, `rows_replayable`, `rows_with_coldkey`, `invalid_json_lines` | Shows whether the export was clean and complete enough to study. |
| `decision_data_blockers`, `decision_data_gaps`, `decision_ready` | Separates "collect more data" from "ready for governance review." |
| `summary_exact_clone_extra_share` | Measures simple copy-paste pressure after identical dedup. |
| `summary_rewritten_clone_extra_share`, `summary_rewritten_clone_group_share` | Measures lightly rewritten K-miner pressure, the main bypass of exact dedup. |
| Per-epoch `base`, `no_identical_dedup`, `no_coldkey_dedup`, `no_dedup` lines | Shows whether one epoch is driving the conclusion. |

Decision-record template:

```text
Sybil / Pareto economics decision:
Chosen policy: keep current dedup | cap/dampen near duplicates | winners-take-most | uncopyable-work first | no scoring-code change
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
- Dedup defaults:
- Pareto/scoring changes:
- Profile pin fields:
- Rollout env gates:

Rollback:
- Disable path:
- Operator notice:
- Follow-up review date:
```

## References

- Dedup implementation: [`lemma/scoring/dedup.py`](../lemma/scoring/dedup.py), used from [`lemma/validator/epoch.py`](../lemma/validator/epoch.py).
- Offline replay helper: [`tools/sybil_replay_analyze.py`](../tools/sybil_replay_analyze.py).
- Incentive overview: [incentive_migration.md](incentive_migration.md), [incentive-roadmap.md](incentive-roadmap.md).
