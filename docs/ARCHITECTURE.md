# Lemma architecture

## Components

- **Protocol** ([lemma/protocol.py](../lemma/protocol.py)): `LemmaChallenge` synapse — validator fills the theorem and toolchain pins; miner fills **`reasoning_steps`** (structured PRM-style list, preferred), optional legacy **`reasoning_trace`**, and **`proof_script`** (full `Submission.lean`).
- **Problems** ([lemma/problems/](../lemma/problems/)): `ProblemSource`. **Default:** `GeneratedProblemSource` expands each epoch’s block seed into one theorem from a fixed template registry (no giant JSON). Template mix and wall-clock expectations: [GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md). **Optional:** `LEMMA_PROBLEM_SOURCE=frozen` + `minif2f_frozen.json` (or build a large catalog via `scripts/build_lemma_catalog.py`; see [CATALOG_SOURCES.md](CATALOG_SOURCES.md)).
- **Lean** ([lemma/lean/](../lemma/lean/)): `materialize_workspace` writes `Challenge` / `Solution` / `Submission` + `lakefile.toml`; `LeanSandbox` runs `lake build` and `#print axioms` via `AxiomCheck.lean` (host or Docker).
- **Judge** ([lemma/judge/](../lemma/judge/)): Pluggable LLM rubric (`AnthropicJudge`, `OpenAIJudge`, `FakeJudge` for dry-runs).
- **Scoring** ([lemma/scoring/](../lemma/scoring/)): Token count (`tiktoken`) + Pareto layers on `(reasoning_score ↑, tokens ↓)` → normalized weights.
- **Miner** ([lemma/miner/](../lemma/miner/)): `bt.Axon` + async `forward` calling `LLMProver`.
- **Validator** ([lemma/validator/](../lemma/validator/)): `bt.Dendrite` broadcast, sandbox verify, judge survivors, `subtensor.set_weights` (commit–reveal handled inside the SDK).

## Governance

Catalog bumps, judge/rubric versions, and env parity across validators are described in [GOVERNANCE.md](GOVERNANCE.md). Operators should align on `lemma meta` (rubric SHA-256) and pinned `JUDGE_*` settings.

## Trust model (v1)

- Reject `sorry` / `admit` / obvious cheats via [lemma/lean/cheats.py](../lemma/lean/cheats.py).
- Allow only Mathlib standard axioms: `propext`, `Quot.sound`, `Classical.choice` (parsed from `#print axioms` output).
- Optional post-verify shell hook ([COMPARATOR.md](COMPARATOR.md)) for experiments toward [leanprover/comparator](https://github.com/leanprover/comparator)-style checks; landrun-style isolation like [lean-eval](https://github.com/leanprover/lean-eval) is not bundled.

## References

- [Bittensor Synapse](https://docs.learnbittensor.org/python-api/html/autoapi/bittensor/core/synapse/index.html)
- [lean-eval](https://github.com/leanprover/lean-eval)
- [miniF2F](https://github.com/openai/miniF2F)
