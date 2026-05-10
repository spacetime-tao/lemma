# Architecture

| Area | Role |
| ---- | ---- |
| [`LemmaChallenge`](../lemma/protocol.py) | Synapse: validator sends theorem; miner returns `proof_script` plus optional metadata. |
| [`lemma/problems/`](../lemma/problems/) | `ProblemSource`. Generated templates ([generated-problems.md](generated-problems.md)); optional frozen JSON ([catalog-sources.md](catalog-sources.md)). |
| [`lemma/lean/`](../lemma/lean/) | Workspace materialization; `LeanSandbox` runs `lake build` + axiom driver. |
| [`lemma/judge/`](../lemma/judge/) | Optional prose-evaluation tooling outside live proof-only rewards. |
| [`lemma/scoring/`](../lemma/scoring/) | Binary proof-pass entries, dedup/reputation, and Pareto → weights. |
| [`lemma/miner/`](../lemma/miner/) | Reference Axon service + `LLMProver` compatibility path; keep competitive strategy and friendly UX out of core ([miner.md](miner.md)). |
| [`lemma/validator/`](../lemma/validator/) | Dendrite broadcast → verify → score → `set_weights`. |

[governance.md](governance.md).

## Trust model (v1)

- Cheat scan ([`cheats.py`](../lemma/lean/cheats.py)).
- Mathlib axiom allowlist from `#print axioms`.

## References

- [Bittensor Synapse](https://docs.learnbittensor.org/python-api/html/autoapi/bittensor/core/synapse/index.html)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F)
