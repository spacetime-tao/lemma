# Transport: Axon, synapse, and integrity (Lemma today)

Lemma validators call miners over **Bittensor’s Dendrite → Axon** path with a single synapse type: [`LemmaChallenge`](../lemma/protocol.py). This document records **why** the synapse carries a **body hash**, and how that relates to broader Bittensor guidance.

## Current path

| Piece | Role |
| --- | --- |
| **Validator** | Opens a **`bt.Dendrite`**, sends [`LemmaChallenge`](../lemma/protocol.py) to each miner **`Axon`**. |
| **Miner** | Axon handler runs the prover / builds the response synapse. |
| **Batching** | [`run_epoch`](../lemma/validator/epoch.py) forwards one synapse per round with `bt.Dendrite`; responses are aligned by UID order. |

This is the **shipping** stack in this repository. It is **not** replaced here by generic HTTP yet.

## Body hash and `required_hash_fields`

`LemmaChallenge` sets **`required_hash_fields`** so Bittensor’s **`Synapse.body_hash`** covers the challenge fields **and** the miner-filled **`reasoning_*`** / **`proof_script`** payload.

Effects:

- **`computed_body_hash`** on the wire is derived from that canonical hash (see Bittensor synapse docs / implementation).
- **`synapse_miner_response_integrity_ok`** recomputes **`body_hash`** and compares it to **`computed_body_hash`**; **missing hash, missing `deadline_block`, or mismatch => drop** (tampering, proxy rewriting, or client skew).

**Not** included in `required_hash_fields` (see class doc / fields): e.g. **`miner_verify_attest_signature_hex`**, **`proof_commitment_hex`**, **`commit_reveal_nonce_hex`** — those use separate crypto or phases. Changing **`required_hash_fields`** requires **coordinated** miner + validator releases because both sides must agree on what gets hashed.

## Relation to subnet knowledge base

[`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) marks **Axon / Dendrite / synapse** as **deprecated for *new* subnet designs** in favor of **HTTP APIs with Epistula signing**. Lemma **still implements** the classic path above for compatibility with the existing miner/validator ecosystem.

**Interpretation:** “Deprecated” here means **greenfield subnets** should not copy Axon-first patterns for new protocols; it does **not** imply Lemma will delete Dendrite support on a fixed date. A future migration would be a **major release** (HTTP endpoints, signing model, discovery), not a flag flip.

## Migration gate

Do not introduce a second validator→miner transport beside Dendrite/Axon as a
partial default. Either keep the current path, or plan an HTTP + Epistula major
release with both miner and validator support changing together.

Minimum design record before migration:

```text
Transport migration decision:
Chosen path: keep Dendrite/Axon | migrate to HTTP + Epistula
Reason:

Compatibility:
- Miner discovery source:
- Auth/signing scheme:
- Request and response schema:
- Body integrity fields:
- Timeout/deadline semantics:
- Cutover block or release tag:

Rollout:
- Dual-stack period, if any:
- Validator fallback policy:
- Miner operator notice:
- Rollback path:
```

The migration should also update [`LemmaChallenge`](../lemma/protocol.py), miner
serving docs, validator querying code, tests for signed request integrity, and
the operator upgrade checklist in [governance.md](governance.md).

## Practical operator notes

- **Proxies / TLS termination:** Anything that strips hash headers or rewrites JSON bodies can break **`computed_body_hash`** matching — treat hash failures as transport bugs or attacks.
- **Version skew:** Miner and validator **Lemma** versions must agree on synapse fields and hashing rules.
- **Forward wait:** Timeouts are chain-derived — see [validator_lean_load.md](validator_lean_load.md) and [validator.md](validator.md).

## References

- Synapse definition + integrity check: [`lemma/protocol.py`](../lemma/protocol.py).
- Epoch drops bad hashes: [`lemma/validator/epoch.py`](../lemma/validator/epoch.py).
- Communication deprecation note: [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) (`communication.axon_dendrite_synapse`).
