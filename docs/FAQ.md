# FAQ

Subnet-wide primer (economics, schedules, inference). Technical Lean/Docker topics follow below.

## Subnet primer

### How does scoring work?

1. **Lean must pass** — wrong proof ⇒ no reward that round (kernel gate).
2. **Among proofs that pass**, the judge scores **how well you explained your thinking** (coherence, exploration, clarity).
3. **Shorter helps at equal quality** — weights use Pareto layers: better scores win, but bloated traces lose to tighter ones ([`lemma/scoring/pareto.py`](../lemma/scoring/pareto.py)).

So it is **not** “chat-only”: proof correctness is mandatory; explanation breaks ties and ranks survivors.

### Where do validators “check” things (and can that use Chutes)?

Rough pipeline **on the validator machine** each scoring round:

1. **Ask miners** over the network (Bittensor dendrite) for a synapse containing **`proof_script`** + reasoning.
2. **Lean check** — build the miner’s `Submission.lean` inside the **Docker sandbox** on the validator (`lake build`, axiom policy, optional comparator). This is **not** Chutes; it’s local CPU/container work.
3. **Judge** — if Lean passes, call the **LLM judge** (configured via **`JUDGE_PROVIDER`**, **`OPENAI_*`**, **`ANTHROPIC_*`**) to score the reasoning trace. That HTTP call **can** go to **Chutes** if you set **`OPENAI_BASE_URL`** (and model/key) to a Chutes OpenAI-compatible endpoint — same as pointing it at vLLM or OpenAI.

**Miners** separately call **their** prover API (often **`PROVER_*`** + Anthropic/OpenAI keys) to *produce* the proof; that can also be Chutes. So: **Chutes hosts inference for LLMs**, not the Lean kernel; Lean stays on the validator.

### Generated vs frozen — how many “questions”?

| Mode | What it is | Size |
| ---- | ---------- | ---- |
| **`LEMMA_PROBLEM_SOURCE=generated`** (default) | Block seed → RNG picks one of **22 templates**; many templates randomize numbers so statements vary a lot. | **Unbounded** distinct challenges over chain life (no fixed “7k cap”). |
| **`frozen`** | Rows in `minif2f_frozen.json` (optional huge rebuild via [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py)). | Exactly **N** rows; repeats eventually. |

Changing templates or frozen JSON is a **consensus upgrade** — align Git tags, **`lemma meta`** (judge + **`generated_registry_sha256`**), and optional **`LEMMA_GENERATED_REGISTRY_SHA256_EXPECTED`** ([GOVERNANCE.md](GOVERNANCE.md)).

For **easy vs medium vs hard mix**, what the **30 topic strings** mean, and how this relates to a **fixed wall-clock budget** (e.g. improving AI within “solve under timeout”), see [GENERATED_PROBLEMS.md](GENERATED_PROBLEMS.md).

### Timeouts — plain English

| Setting | Meaning |
| ------- | ------- |
| **`DENDRITE_TIMEOUT_S`** | Max time to wait for **one miner HTTP response** (one challenge). **Default `3600`** (60 minutes) in config; subnets should align the same value across validators. |
| **`LEAN_VERIFY_TIMEOUT_S`** | Max time for **`lake build`** + checks inside the validator sandbox for **that submission**. **Default `3600`** (60 minutes) in config; lower if all validators agree. |

These do **not** set “how many rounds per day.” **Round frequency** comes from **Bittensor subnet tempo / epochs** ([Bittensor docs](https://docs.learnbittensor.org/)). Fewer rounds/day is the cleanest lever to cut miner spend.

### Economics (illustrative)

Your **$0.50/problem × rounds/day** sketch depends on **provider pricing**, **tokens per proof**, and **how often miners are queried**. Lower spend usually means: **fewer scored epochs** (subnet policy), **cheaper/smaller prover**, **shorter outputs**, or **self-hosted / discounted inference**. No single timeout number fixes budget by itself.

### Inference APIs — what about Chutes?

[**Chutes**](https://chutes.ai/) runs **open-source models** as serverless inference ([overview](https://chutes.ai/), [GitHub org](https://github.com/chutesai)). Plans like **$3/mo** are **not** “unlimited mining for three dollars”: they give a **monthly usage credit** (e.g. “5×” pay-as-you-go value) plus **per-day request** and **burst** caps. If each prover call costs real money at the token meter, the **credit is used up fast**; overages fall back to normal PAYG. Miners only need an **OpenAI-compatible HTTP API**: set **`PROVER_PROVIDER=openai`**, **`OPENAI_BASE_URL`**, **`OPENAI_MODEL`**, **`OPENAI_API_KEY`**. **DENDRITE_TIMEOUT_S** (default 60 minutes in shipped config) is separate from Chutes billing — it’s how long the **validator waits** for your answer, not your monthly bill.

**Affine (Subnet 64) vs Lemma:** Affine’s rules say validators must **grade miners by running the miner’s model on Chutes** (one shared evaluation path). **Lemma** does not use that rule: your prover can be Chutes, Claude, or a home GPU—**Subnet 64’s emissions do not pay Lemma miners**; only **your Lemma subnet’s** incentives (**ALPHA** / subnet emissions — see [Bittensor emissions](https://learnbittensor.org/concepts/tokenomics/emissions) and [Dynamic TAO](https://learnbittensor.org/concepts/dynamic-tao/subnet-pool)) and your own API budget apply.

### Can Lemma use Chutes in an Affine-*like* way (any Chutes model)?

**As plumbing: yes.** Lemma only needs **HTTP APIs**. If [Chutes](https://chutes.ai/) exposes an **OpenAI-compatible** base URL for a model, you can point:

- **Miner prover:** `PROVER_PROVIDER=openai`, `OPENAI_BASE_URL=<Chutes endpoint>`, `OPENAI_MODEL=<model id on Chutes>`, `OPENAI_API_KEY=<your Chutes key>` (same pattern as vLLM or OpenAI).
- **Validator judge (optional):** `JUDGE_PROVIDER=openai` with the **same style** of URL/model — and **`lemma meta`** + **`JUDGE_PROFILE_SHA256_EXPECTED`** so every validator uses **one** agreed judge stack.

**As “Affine-identical” governance: not automatically.** Affine’s subnet consensus **forces** a specific evaluation path (miners commit models on Chutes; validators check there). Lemma’s codebase does **not** on-chain enforce “you must use Chutes model X.” Your subnet *can* adopt that **socially** (operator agreement, monitoring, slashing policy) or extend the client later — but it is **not** wired like Affine out of the box.

### Rough monthly miner cost (not financial advice)

Use a **budget formula**, not a single universal number:

**≈ (number of challenges you answer per month) × (average dollars per challenge)**

“Dollars per challenge” ≈ **(input tokens + output tokens) × price per million tokens** on whatever host you use (Chutes PAYG after credits, Anthropic, etc.). Chutes **subscription credits** only reduce the bill until the credit cap / burst limits are hit; then you’re on PAYG.

**Examples (illustrative only):**

| Answered / month | ~$/challenge | ~Monthly inference |
| ----------------: | -----------: | -------------------: |
| 2,000 | $0.0075 | ~**$15** |
| 2,000 | $0.05 | ~**$100** |

A **“24/7”** story like **~288 challenges/day** ⇒ about **8,600+/month** *if* you are actually invoked that often. At that volume, **$15–100/mo** only works if the **average cost per challenge** is about **$0.002–$0.012** (cheap model, modest output). A **$0.50/challenge** rough guess at the *same* volume is on the order of **~$4,000+/month** in inference alone — not $0.50×288 per **day** unless you also pay that rate on **every** minute of the day. Your real numbers depend on **epoch rate**, **whether validators query you every round**, **model $/token**, and **output size**; measure a week of logs and multiply.

**$15/mo** and **$100/mo** are plausible **ballparks** for *some* setups; they are **not** automatic for all miners.

### Where are miners’ answers stored, and who can see them?

**There is no central Lemma “cloud vault” of all proofs** in this repo.

- **In flight:** When a validator queries a miner, the answer (Lean `proof_script` + reasoning) travels over the **network to that validator** and is held **in memory** for the round. It is not automatically uploaded to a shared website.
- **On the chain:** Bittensor records **weights / emissions** (high-level scores), **not** full proof text—storage would be impossibly large.
- **Optional copy on a validator:** Set **`LEMMA_TRAINING_EXPORT_JSONL`** to a file path. Each epoch can append **one JSON line per judged miner** with `theorem_id`, **`model_card`** (which prover the miner reports), `proof_script`, reasoning text/steps, rubric scores, block, uid ([`training_export.py`](../lemma/validator/training_export.py)). **Anyone with access to that validator’s disk** (or wherever you ship the file—S3, etc.) can inspect answers.
- **Your own miner:** You can always **log** completions locally if you add tooling around `LLMProver`; not bundled by default.

### How LLM “tokens” and pricing work (e.g. Chutes $/M “in” / “out”)

Providers bill **language-model usage** in **tokens** (chunks of text—roughly ~4 characters per token for English; code can differ).

- **Input (“in”) tokens:** Everything you send in the prompt (theorem statement, instructions, chat history).
- **Output (“out”) tokens:** Everything the model **generates** (Lean proof, reasoning steps). **Output is often priced higher per million** because generation is more compute-heavy.

**Rough cost for one prover call:**

\[
\text{USD} \approx \frac{N_{\text{in}}}{10^6} \times P_{\text{in}} + \frac{N_{\text{out}}}{10^6} \times P_{\text{out}}
\]

where \(P_{\text{in}}\) / \(P_{\text{out}}\) are dollars **per million tokens** from the catalog (e.g. Chutes cards showing **$0.08/M in** and **$0.24/M out** for **Qwen3 32B TEE**).

**Worked example (illustrative):** one challenge uses **4k input** + **8k output** tokens on that model:

- Input cost ≈ \(4000/10^6 \times 0.08\) ≈ **$0.00032**
- Output cost ≈ \(8000/10^6 \times 0.24\) ≈ **$0.00192**
- **~$0.0022 per challenge** before subscription credits

Same tokens on a **frontier** card (e.g. **~$0.44/M in, $2.00/M out**):

- ≈ \(4000/10^6×0.44 + 8000/10^6×2.00\) ≈ **$0.0178** per challenge

Multiply by **how many challenges/month** you actually run to bracket monthly inference. Your screenshot models span a **wide** range—always read **current** cards on [Chutes](https://chutes.ai/).

**Super simple example (same 4k in / 8k out every time, Qwen3 32B TEE = $0.08/M in, $0.24/M out):**

- **One challenge** ≈ **$0.0022** (as above).
- **72 challenges/day** (e.g. every ~20 minutes) → ~**$0.16/day** → ~**$4.7/mo** inference-only.
- **288 challenges/day** (one every 5 minutes) → ~**$0.63/day** → ~**$19/mo** inference-only *if* token sizes really stay that small.

If output balloons to **32k tokens** on the same price card, output cost alone is \((32000/10^6)×0.24 ≈ \$0.0077\) per call before input—**token count dominates**, not the 5‑minute wall clock.

### Training data: do we need a validator, and can we put it on GitHub?

- **Collecting data for PRM / research:** you want **at least one honest validator** (or several) with **`LEMMA_TRAINING_EXPORT_JSONL`** enabled, then **merge** lines from different machines if you run more than one (dedupe on `block`+`uid`+`theorem_id` as needed). **Subnet operators / whoever runs validators** usually drive publishing—not “automatic” from the chain.
- **Not auto-uploaded:** the env var is just a **local file path** on that machine. Lemma **does not** send it to GitHub, S3, or anywhere else. You add your own `cron`/CI upload if you want a public dataset.
- **What’s inside each row:** exports include miners who **passed Lean** and got a **successful judge JSON** that epoch. Rows contain **`proof_script`**, reasoning, **`rubric`** scores, etc. **Failed Lean proofs are not written** to this JSONL path (they never reached scoring). A **low rubric composite** usually means “passed Lean but weak explanation,” not “kernel failure”—that nuance matters for dataset filtering. **Low-score rows are still “good” for ML** if you want labels for weak reasoning; filter by `rubric.composite` when you only want high-quality traces.
- **Public hosting:** **Yes, it’s possible**—e.g. periodic **uploads to a GitHub Release** (compressed `.jsonl.gz`), or **[Hugging Face Datasets](https://huggingface.co/datasets)**. Treat publication like any ML dataset: license, consent, **no secrets**. Researchers can **drop or down-weight low rubric rows** if they only want high-quality traces.
- Lemma doesn’t auto-push to GitHub; **subnet ops** own the pipeline (cron → S3 → release).

### How can “Lean fail”? (plain English)

The validator builds the miner’s `Submission.lean` in Docker and runs `lake build` plus checks. **Failure** means no passing proof for that miner this round—common reasons map to [`VerifyResult.reason`](../lemma/lean/sandbox.py):

| Reason (internal) | Plain meaning |
| ----------------- | --------------- |
| **`compile_error`** | Lean couldn’t build (syntax/type error, wrong theorem name, missing imports). |
| **`axiom_violation`** | Proof depends on axioms outside the subnet’s **allowed** list. |
| **`cheat_token`** | Submission used banned tokens (`sorry`, `admit`, …) or user-declared axioms. |
| **`timeout` / `oom`** | Build or check ran too long or used too much memory. |
| **`docker_error`** | Sandbox/runtime problem (image missing, daemon issue). |
| **`comparator_rejected`** | Optional extra hook failed ([COMPARATOR.md](COMPARATOR.md)). |

So **“Lean failed”** isn’t only “wrong math”—often it’s **doesn’t compile** or **breaks rules**. **No JSONL row** for that miner usually means one of the above or a **judge error** (bad JSON / API down)—not “saved as a wrong answer row.”

### What does the LLM judge see, and what gets saved?

- **Prompts** live in [`lemma/judge/prompts.py`](../lemma/judge/prompts.py): a **system** message that the judge is scoring **informal reasoning** (not re-checking the kernel) and must answer with **one line of JSON** only: `coherence`, `exploration`, `clarity` (each 0.0–1.0). The **user** message includes the **theorem text**, the **miner’s trace**, and the **Lean proof** for context.
- **What the model returns:** the code **parses only that JSON** ([`json_util.py`](../lemma/judge/json_util.py)). A **composite** score is the average of the three numbers. If the model chatters in prose, we still try to extract the first `{...}` object—**prose is not what we store.**
- **What lands in `LEMMA_TRAINING_EXPORT_JSONL`:** the **`rubric` dict** (those four numbers), plus miner **proof** and **reasoning** — **not** a separate “judge essay” field. There is no first-class place today for the judge’s free-form chain-of-thought (and the prompt **discourages** it).

### Can miners cap how many problems they answer per day?

**Yes.** Set **`MINER_MAX_FORWARDS_PER_DAY`** or run **`lemma miner --max-forwards-per-day N`**. After **N** successful forwards in a **UTC** day, further validator requests get **429** until the next day (state in `~/.lemma/miner_daily_forwards.json`). See [MINER.md](MINER.md).

### Which model do validators use for judging, and how is that enforced?

**“openai” here is not the company and not “ChatGPT’s model family.”** In this repo, **`JUDGE_PROVIDER=openai`** means: *use the Python path that talks over the **OpenAI-style HTTP API*** (same JSON routes many servers copied: `/v1/chat/completions`). The **weights** you load are whatever id your **inference server** understands—for example **`Qwen/Qwen3-32B-TEE`** on [Chutes](https://chutes.ai/) or an open-weight id served by **vLLM**. If you pointed **`OPENAI_BASE_URL`** at **api.openai.com**, then **`OPENAI_MODEL`** would be an **OpenAI product** name like `gpt-4o`. One protocol, many possible backends.

- **Defaults** ship as **`JUDGE_PROVIDER=openai`** with **`OPENAI_MODEL=Qwen/Qwen3-32B-TEE`** and **`OPENAI_BASE_URL=https://llm.chutes.ai/v1`** ([`.env.example`](../.env.example)). See [MODELS.md](MODELS.md) for validator vs miner guidance and how to list live ids. “OpenAI-compatible” means **any host** that speaks that HTTP shape: **Chutes**, **self-hosted vLLM**, **OpenAI proper**, **Azure OpenAI**, etc.
- **Fairness** comes from **every validator using the same judge recipe**: same **model id**, **temperature**, **max tokens**, **base URL shape** (embedded in **`lemma meta`** → **`judge_profile_sha256`**). Set **`JUDGE_PROFILE_SHA256_EXPECTED`** so a validator **refuses to start** if someone typos the model or URL.
- **“Platform” doesn’t matter** to the code—only that the API returns completions the parser understands. Two validators could both use the **same model id** from **different** base URLs **only if** those stacks behave identically enough that operators accept one **`judge_profile_sha256`** (usually you standardize one **`OPENAI_BASE_URL`** + **`OPENAI_MODEL`** pair).

### Can outsiders see which LLM each miner used?

Miners send an optional **`model_card`** string on the synapse; the reference miner fills it from **`PROVER_*`** / **`OPENAI_*`** settings (`prover=openai model=… base_url=…`) so **JSONL exports** can slice training rows **by backend/model**. It’s **self-reported**—subnet policy could require honesty; cheating the label doesn’t bypass Lean.

### Does the “best model” matter for the leaderboard?

**All that ultimately matters for rewards is:** valid Lean proof + judged reasoning quality + Pareto token efficiency. A **small** model that passes Lean and writes clear steps can beat a huge model that rambles—**which is the point** of separating kernel check from trace grading. Model labels are **analytics** (who gets quality per dollar), not a separate score column unless your subnet adds one.

### Do validators “combine” miner answers into one?

**No.** Each **validator** runs its own round: it **broadcasts the theorem** to miners, **collects each miner’s reply separately**, **checks Lean + judges traces per miner**, then writes **weights** (who gets how much incentive credit). There is **no** step where validators merge all proofs into a single “combined answer.” Different validators may run at slightly different times; the **chain** aggregates **emissions / consensus over validators** at the protocol level—that’s not Lemma stitching proofs together.

Validators **do** agree off-chain on **the same challenge** in Lemma because they **deterministically generate the same theorem** from the block seed (**generated** mode) or the same catalog row (**frozen** mode).

---

### Where do traces and scores show up (quick recap)?

Validators log **`lemma_epoch_summary`**; optional **`LEMMA_TRAINING_EXPORT_JSONL`** appends judged rows for analytics. There is **no built-in public dashboard** — ship JSONL/logs to your BI stack ([PRODUCTION.md](PRODUCTION.md)).

### Why CI runs `lake build` on every template

Templates are **Lean text**. Unit tests only prove Python runs — **not** that Mathlib syntax/types are valid. One bad line → validators/miners see mysterious build failures on mainnet. CI runs [`scripts/ci_verify_generated_templates.py`](../scripts/ci_verify_generated_templates.py) (Docker) so each template **compiles** with a stub `Submission` before release.

### Testing on testnet (e.g. `NETUID=467`)

Lemma cannot dial your wallets remotely. **You** run:

1. Install Lemma (`uv sync`), configure `.env`: **`SUBTENSOR_NETWORK`**, **`SUBTENSOR_CHAIN_ENDPOINT`** (testnet), **`NETUID=467`**, wallets (**cold/hot names** — your `lemma`/`lemmahot` miner and `test`/`testhot` validator).
2. Register keys on the subnet (`btcli`) per [Bittensor wallets / subnets](https://docs.learnbittensor.org/).
3. **Miner:** `lemma miner` with axon reachable; **prover** keys or local model.
4. **Validator:** build Lean image (`scripts/prebuild_lean_image.sh`), set judge (`lemma meta`), run `lemma validator` (start with `--dry-run` / `LEMMA_FAKE_JUDGE=1` if iterating).
5. Watch logs for **`lemma_epoch_summary`** and verify **`set_weights`** when ready.

Exact endpoints and faucet TAO for testnet change over time — follow current [Bittensor local/testnet docs](https://docs.learnbittensor.org/).

---

## Why Lean 4?

Kernel-checked proofs give an objective pass/fail gate before any LLM judge runs.

## Why Docker for verification?

Validators execute untrusted Lean from miners. Docker provides cgroup limits, optional `--network none`, and a reproducible toolchain + Mathlib cache.

## `lake build` is slow on first run

Run `lake exe cache get` once (or bake the [compose/lean.Dockerfile](../compose/lean.Dockerfile) image) so Mathlib `olean` artifacts are warm.

## How do I add more theorems?

- **Default (generated):** edit the template registry in [`lemma/problems/generated.py`](../lemma/problems/generated.py) (consensus upgrade — see [GOVERNANCE.md](GOVERNANCE.md)).
- **Frozen mode:** run [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py) or `scripts/load_minif2f.py`, or hand-edit JSON (keep `lean_toolchain` / `mathlib_rev` aligned with the sandbox image).

## What if `set_weights` fails?

- Confirm the hotkey is registered as a **validator** on the subnet.
- Check rate limits and commit–reveal settings in [Bittensor docs](https://docs.learnbittensor.org/concepts/commit-reveal/).
- Use `lemma validator --dry-run` to debug scoring without chain writes.

## Affine uses “one evaluation path”; is Lemma the same?

Not quite. **Affine** routes validator evaluation through **miners’ models on Chutes** (Subnet 64); their FAQ describes burning emissions when evaluation could be **bypassed** (e.g. routing traffic to **GPT-4o** instead of the committed model). That’s **one enforced inference surface** for scoring miners’ models.

**Lemma** uses a **small LLM judge** only for **reasoning-trace quality**, after **Lean** passes. Supporting Anthropic **or** OpenAI is **operator choice** (keys, cost); for **fair, comparable scores across miners**, subnet operators should **pin one `JUDGE_PROVIDER` + model + `JUDGE_TEMPERATURE` / `JUDGE_MAX_TOKENS`** for all validators—same idea as “one grader,” even though the code allows two backends.

## Five minutes vs “thousands of problems”

**`DENDRITE_TIMEOUT_S`** is **one HTTP timeout per challenge** (miners responding to **one** theorem broadcast). Each **chain epoch**, the validator samples **one** problem (**generated** from the block seed by default; **frozen** walks JSON). Throughput is **one problem per scoring epoch**, not thousands per wall-clock minute.

### Why not millions of rows forever?

**Generated mode (default):** [`GeneratedProblemSource`](../lemma/problems/generated.py) turns each epoch seed into a theorem from a fixed template list—**effectively unbounded variety** without shipping huge JSON. Changing templates is a **consensus upgrade** (like swapping catalogs).

**Frozen mode:** the JSON list is finite; at high tempo you will see repeats. Rebuild or rotate the file with [`scripts/build_lemma_catalog.py`](../scripts/build_lemma_catalog.py) if you use `LEMMA_PROBLEM_SOURCE=frozen`.

## `lemma --help` used to show Bittensor argparse

The Bittensor SDK registers a global CLI when imported. The Lemma CLI **lazy-imports** `bittensor` inside subcommands so `lemma --help` stays a normal Click help screen.

## Comparator / landrun?

v1 uses `lake build` + axiom whitelist + cheat scan. For maximum assurance against statement smuggling, plan an upgrade to [comparator](https://github.com/leanprover/comparator) per [lean-eval](https://github.com/leanprover/lean-eval).
