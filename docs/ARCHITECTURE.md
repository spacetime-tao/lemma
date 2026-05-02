# Architecture

| Area | Role |
| ---- | ---- |
| [`LemmaChallenge`](../lemma/protocol.py) | Synapse: validator fills theorem + toolchain pins; miner returns **`reasoning_steps`** / **`reasoning_trace`** / **`proof_script`**. |
| [`lemma/problems/`](../lemma/problems/) | **`ProblemSource`**. Default generated templates ([GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md)); optional frozen JSON ([CATALOG_SOURCES.md](CATALOG_SOURCES.md)). |
| [`lemma/lean/`](../lemma/lean/) | **`materialize_workspace`** builds Lake layout; **`LeanSandbox`** runs **`lake build`** + axiom driver (Docker or host). |
| [`lemma/judge/`](../lemma/judge/) | Anthropic / OpenAI-compatible / **`FakeJudge`**. |
| [`lemma/scoring/`](../lemma/scoring/) | Token counts + Pareto ranking → weights. |
| [`lemma/miner/`](../lemma/miner/) | Axon + **`LLMProver`**. |
| [`lemma/validator/`](../lemma/validator/) | Dendrite broadcast → verify → judge → **`set_weights`**. |

Governance: [GOVERNANCE.md](GOVERNANCE.md).

## Trust model (v1)

- Cheat scan ([`cheats.py`](../lemma/lean/cheats.py)).
- Mathlib axiom allowlist from **`#print axioms`**.
- Optional comparator ([COMPARATOR.md](COMPARATOR.md)).

## References

- [Bittensor Synapse](https://docs.learnbittensor.org/python-api/html/autoapi/bittensor/core/synapse/index.html)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F)
