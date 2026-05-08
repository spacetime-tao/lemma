# Sybil economics and identity (operators)

Lemma scoring includes **deduplication** knobs that reduce certain multi-account games — they are **not** a substitute for sybil resistance on Bittensor.

Canonical machine-readable notes: [`knowledge/sybil.realities.yaml`](../knowledge/sybil.realities.yaml).

## What Lemma actually does

| Mechanism | Env | Purpose |
| --- | --- | --- |
| **Identical submission dedup** | `LEMMA_SCORING_DEDUP_IDENTICAL` (default on) | Same `(theorem_statement, proof_script, reasoning trace)` fingerprint → keep **best** `reasoning_score` only ([`dedup.py`](../lemma/scoring/dedup.py)). Reduces copy-paste clutter in one epoch. |
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

## References

- Dedup implementation: [`lemma/scoring/dedup.py`](../lemma/scoring/dedup.py), used from [`lemma/validator/epoch.py`](../lemma/validator/epoch.py).
- Incentive overview: [incentive_migration.md](incentive_migration.md), [incentive-roadmap.md](incentive-roadmap.md).
