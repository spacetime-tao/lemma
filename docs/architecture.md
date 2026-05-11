# Architecture

Lemma has one main loop:

1. Validator sends a theorem to miners.
2. Miners return `proof_script`.
3. Validator checks each proof with Lean.
4. Passing proofs enter scoring.
5. Validator writes weights.

## Main Parts

| Area | Role |
| --- | --- |
| [`LemmaChallenge`](../lemma/protocol.py) | The Bittensor synapse. It carries the theorem and returned proof. |
| [`lemma/problems/`](../lemma/problems/) | Problem sources: generated templates and optional frozen JSON. |
| [`lemma/lean/`](../lemma/lean/) | Builds Lean workspaces and runs `lake build`. |
| [`lemma/scoring/`](../lemma/scoring/) | Turns passing proofs into weights. |
| [`lemma/miner/`](../lemma/miner/) | Reference miner service and prover client. |
| [`lemma/validator/`](../lemma/validator/) | Broadcasts challenges, checks proofs, scores, and calls `set_weights`. |
| [`lemma/judge/`](../lemma/judge/) | Local prose utilities. Not live validator scoring. |

## Trust Model

Lean is the proof gate. Around it, Lemma also checks:

- banned proof tokens in [`cheats.py`](../lemma/lean/cheats.py);
- allowed axioms from `#print axioms`;
- fixed problem and registry pins;
- shared validator profile hashes.

More policy detail: [governance.md](governance.md).

## References

- [Bittensor Synapse](https://docs.learnbittensor.org/python-api/html/autoapi/bittensor/core/synapse/index.html)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F)
