# Inference models (Chutes)

Lemma talks to LLMs only through **OpenAI-compatible HTTP** (`/v1/chat/completions`). [Chutes](https://chutes.ai/) is the **recommended** host for both **validators** (judge) and **miners** (prover): one billing surface, uniform base URL, and live pricing.

## Live catalog

Authoritative model ids and USD pricing come from Chutes’ listing:

```bash
curl -sS https://llm.chutes.ai/v1/models | jq '.data[] | {id, pricing}'
```

Use the returned **`id`** string as **`OPENAI_MODEL`** (judge or miner prover). Keys and base URL are documented in Chutes’ developer materials (`OPENAI_BASE_URL=https://llm.chutes.ai/v1`).

## Validators (judge)

**Requirement:** every validator on a subnet should share **one** pinned stack (`lemma meta` → **`judge_profile_sha256`** → optional **`JUDGE_PROFILE_SHA256_EXPECTED`**).

**Recommended default:** **`Qwen/Qwen3-32B-TEE`** on **`https://llm.chutes.ai/v1`**.

**Why this model for judging**

- The judge only emits a **short JSON rubric** (instruction-following and structured output matter more than frontier reasoning depth).
- **`Qwen/Qwen3-32B-TEE`** advertises **`json_mode`**, **`structured_outputs`**, and **`reasoning`** on the catalog; it is among the **most cost-efficient** mid-size instruct models on Chutes while still strong on general tasks.
- **“Frontier”** slots on the leaderboard (very large MoE models, premium multimodal stacks) are typically **many times more expensive per token** with little benefit for a tiny judge completion—reserve those only if operators explicitly want that spend.

**When to switch:** If the subnet later standardizes on another id (e.g. a different Chutes deployment or self-hosted vLLM), update env everywhere, rerun **`lemma meta`**, and redistribute the new **`judge_profile_sha256`**.

## Miners (prover)

Miners may use **any** prover that can produce valid **`Submission.lean`**; cost and capability trade off.

| Goal | Chutes ids to consider (check live pricing) |
|------|---------------------------------------------|
| **Lowest spend / experimentation** | Small instruct models (e.g. **Hermes-4-14B**, **Mistral-Nemo-Instruct**, tiny Llama instruct variants)—verify **`json_mode`** / fit for your prompts. |
| **Coding-heavy proofs** | **Qwen/Qwen2.5-Coder-32B-Instruct** is priced for code workloads on Chutes; good match for Lean-shaped outputs if your pipeline uses it as the prover. |
| **Strong reasoning, still moderate cost** | **Qwen/Qwen3-Next-80B-A3B-Instruct**, **deepseek-ai/DeepSeek-V3.2-TEE**, **deepseek-ai/DeepSeek-V3.1-TEE**—compare output $/M and latency to your forward volume. |
| **Maximum capability / budget** | **Frontier**-tier cards (e.g. large Qwen3.5 MoE, **Kimi**, **GLM-5.1**, **DeepSeek-R1**)—use when proof quality gains outweigh token cost. |

Set **`PROVER_PROVIDER=openai`**, point **`OPENAI_BASE_URL`** at Chutes, set **`OPENAI_MODEL`** to the chosen **`id`**, and put **`OPENAI_API_KEY`** to your Chutes key. **`model_card`** on the synapse should reflect what you actually run so training exports stay interpretable.

## Self-hosted vLLM

Defaults in this repo target **Chutes** first. If you instead run [vLLM](https://github.com/vllm-project/vllm) locally, set **`OPENAI_BASE_URL=http://127.0.0.1:8000/v1`** (or `host.docker.internal` from Docker) and **`OPENAI_MODEL`** to whatever id your server loads—then realign **`lemma meta`** with your operators.
