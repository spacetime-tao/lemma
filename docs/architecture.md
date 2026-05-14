# Architecture

| Area | Role |
| ---- | ---- |
| [`LemmaChallenge`](../lemma/protocol.py) | Synapse: validator sends theorem; miner returns `proof_script` plus optional metadata. |
| [`lemma/problems/`](../lemma/problems/) | `ProblemSource`. Default hybrid supply ([catalog-sources.md](catalog-sources.md)); generated templates ([generated-problems.md](generated-problems.md)); optional frozen JSON. |
| [`lemma/lean/`](../lemma/lean/) | Workspace materialization; `LeanSandbox` runs `lake build` + axiom driver. |
| [`lemma/judge/`](../lemma/judge/) | Local file-based prose utilities outside validator scoring. |
| [`lemma/scoring/`](../lemma/scoring/) | Difficulty-weighted rolling scores and same-coldkey partitioning -> weights. |
| [`lemma/miner/`](../lemma/miner/) | Reference Axon service + `LLMProver` compatibility path; keep competitive strategy and friendly UX out of core ([miner.md](miner.md)). |
| [`lemma/validator/`](../lemma/validator/) | Dendrite broadcast → verify → score → `set_weights`. |

[governance.md](governance.md).

## Trust model

Lemma's live protocol is trust-minimized, not trust-free.

The reward-critical path should rely on:

- Lean checking a submitted `proof_script` against the published theorem;
- the pinned Lean toolchain, Mathlib revision, and sandbox image;
- public registry/profile hashes that let operators compare the problem supply
  and reward-relevant validator config;
- reproducible logs or exports that let a third party rerun the same theorem,
  proof, toolchain, and image.

The reward-critical path should not rely on:

- miner prose, model claims, or informal reasoning;
- validator-held secret problem sets;
- generated problem secrecy, since the default supply is public and
  deterministic;
- registry hashes as a quality seal. Hashes prove alignment with a release, not
  that the templates, licenses, or open-problem formalizations are good.

Remaining trust surfaces include the Lean/Mathlib/Docker supply chain, operator
host and key security, Bittensor chain/RPC behavior, and human mathematical
review for open-problem statement faithfulness.

Local enforcement tools:

- cheat scan ([`cheats.py`](../lemma/lean/cheats.py));
- Mathlib axiom allowlist from `#print axioms`;
- generated-template Docker witness gate
  ([`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py)).

## References

- [Bittensor Synapse](https://docs.learnbittensor.org/python-api/html/autoapi/bittensor/core/synapse/index.html)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F)
