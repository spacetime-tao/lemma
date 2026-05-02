# Architecture

| Area | Role |
| ---- | ---- |
| [`LemmaChallenge`](../lemma/protocol.py) | Synapse: validator sends theorem; miner returns reasoning + `proof_script`. |
| [`lemma/problems/`](../lemma/problems/) | `ProblemSource`. Generated templates ([GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md)); optional frozen JSON ([CATALOG_SOURCES.md](CATALOG_SOURCES.md)). |
| [`lemma/lean/`](../lemma/lean/) | Workspace materialization; `LeanSandbox` runs `lake build` + axiom driver. |
| [`lemma/judge/`](../lemma/judge/) | Anthropic / OpenAI-compatible / `FakeJudge`. |
| [`lemma/scoring/`](../lemma/scoring/) | Token counts + Pareto → weights. |
| [`lemma/miner/`](../lemma/miner/) | Axon + `LLMProver`. |
| [`lemma/validator/`](../lemma/validator/) | Dendrite broadcast → verify → judge → `set_weights`. |

[GOVERNANCE.md](GOVERNANCE.md).

## Trust model (v1)

- Cheat scan ([`cheats.py`](../lemma/lean/cheats.py)).
- Mathlib axiom allowlist from `#print axioms`.
- Optional comparator ([COMPARATOR.md](COMPARATOR.md)).

## References

- [Bittensor Synapse](https://docs.learnbittensor.org/python-api/html/autoapi/bittensor/core/synapse/index.html)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F)
