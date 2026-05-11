# Transport: Axon, Synapse, And Integrity

Lemma validators call miners through Bittensor Dendrite/Axon today.

The synapse type is [`LemmaChallenge`](../lemma/protocol.py).

## Current Path

| Piece | Role |
| --- | --- |
| Validator | Uses `bt.Dendrite` to send a challenge. |
| Miner | Axon handler runs the prover and returns a proof. |
| Epoch code | [`run_epoch`](../lemma/validator/epoch.py) sends one synapse per round and aligns responses by UID. |

This is the shipping stack. Generic HTTP has not replaced it.

## Body Hash

`LemmaChallenge.required_hash_fields` makes Bittensor hash the challenge fields
and miner-filled `proof_script`.

The validator recomputes `body_hash` and compares it to `computed_body_hash`.

Drop the response when:

- hash is missing;
- `deadline_block` is missing;
- hash does not match.

This catches tampering, proxy rewriting, and version skew.

Some fields are not part of `required_hash_fields` because they have their own
checks, such as:

- `miner_verify_attest_signature_hex`;
- `proof_commitment_hex`;
- `commit_reveal_nonce_hex`.

Changing `required_hash_fields` needs a coordinated miner and validator release.

## HTTP + Epistula

[`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml) says
new subnet designs should prefer HTTP APIs with Epistula signing.

Lemma still uses Dendrite/Axon for compatibility.

Moving to HTTP + Epistula would be a major release, not a flag flip.

## Migration Gate

Do not add a second default transport casually.

Before migrating, write a design record with:

- chosen path;
- miner discovery source;
- auth and signing;
- request and response schema;
- body integrity fields;
- timeout rules;
- cutover block or release tag;
- rollback path.

The migration must update protocol code, miner serving docs, validator query
code, integrity tests, and [governance.md](governance.md).

## Operator Notes

- Proxies that rewrite bodies or strip hash headers can break responses.
- Miner and validator versions must agree on synapse fields.
- Forward wait is chain-derived. See [validator_lean_load.md](validator_lean_load.md).

## References

- [`lemma/protocol.py`](../lemma/protocol.py)
- [`lemma/validator/epoch.py`](../lemma/validator/epoch.py)
- [`knowledge/subnet.invariants.yaml`](../knowledge/subnet.invariants.yaml)
