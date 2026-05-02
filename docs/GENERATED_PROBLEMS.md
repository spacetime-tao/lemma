# Generated problems (default mode)

When **`LEMMA_PROBLEM_SOURCE=generated`** (the default), validators do **not** read a huge frozen JSON bank. They expand a **shared integer seed** (tied to the epoch / block) into **one** theorem per round using a **fixed, ordered list of templates** in [`lemma/problems/generated.py`](../lemma/problems/generated.py). Everyone with the same code and seed gets the **same** `Problem`.

## What miners actually see

- **22 templates** in the registry: **7** tagged `easy`, **11** `medium`, **4** `hard` (see `_RAW_BUILDERS` in the source).
- **Selection:** for each seed, the implementation draws **uniformly** among all **22** templates. So *per challenge* (ignoring any subnet policy that filters by split), the **approximate** chances are:
  - **~32%** easy (7/22)
  - **50%** medium (11/22)
  - **~18%** hard (4/22)
- **“30 topics”:** the tuple `TOPICS` has **30** string labels (algebra, analysis, number theory, etc.). A label is attached **at random** for logging and exports; it is **not** a separate set of 30 problem shapes. The **shape** of the math comes from the **template** (e.g. a concrete `Nat` addition fact vs. a universal statement vs. a “hard” classic proof).

**Easy** templates are mostly small goals suitable for automation (`norm_num`, `rfl`, short `simp` chains): `True`, concrete natural/real equalities and inequalities, simple bool/list/finset facts.

**Medium** templates are typical Mathlib-sized exercises: commutativity/associativity-style statements, basic analysis (`abs` triangle inequality, continuity of the identity), a fixed 2×2 determinant, and similar.

**Hard** templates are **substantial** formal proofs in spirit (e.g. infinitely many primes, irrationality of √2, a nontrivial `Finset` inequality). They are *meant* to be challenging for an LLM that must emit **valid Lean** in one shot.

## Wall-clock budget (`DENDRITE_TIMEOUT_S`)

The generator does **not** encode a time limit. **`DENDRITE_TIMEOUT_S`** is how long the validator waits for **each miner’s HTTP response** for **that epoch’s single challenge**.

**Shipped default:** **`3600` seconds (60 minutes)** — see [`lemma/common/config.py`](../lemma/common/config.py) and [`.env.example`](../.env.example). Other values are fine only if **every** subnet validator agrees.

**Subnet uniformity:** every validator **should** run the **same** **`DENDRITE_TIMEOUT_S`** (and the same judge/problem settings). Lemma does **not** on-chain enforce equality—operators coordinate via releases, ops chats, and **`lemma meta`** — but **different** timeouts mean **different** scoring rounds (who timed out vs succeeded), so mismatched values are unfair. **Practical checklist** (pinning image, shared env, `JUDGE_PROFILE_SHA256_EXPECTED`, etc.): [GOVERNANCE.md — Validator parity checklist](GOVERNANCE.md#keeping-every-validator-on-the-same-lemma-parity-checklist).

**`LEAN_VERIFY_TIMEOUT_S`** is separate: max time for **`lake build`** on the validator after the answer arrives (shipped default **3600 s** to match prover headroom; subnets may standardize lower if aligned).

## Wall-clock budget — expectations

**Qualitative expectation:** with a fixed window of a few minutes, **easy and many medium** templates are often **plausible** to close if the prover and Mathlib usage are strong. **Hard** templates will **often** cause timeouts or failed builds in that same window unless the stack is very capable or specialized—so *empirical* success rates depend on model, prompts, and hardware. The point of reporting the **7 / 11 / 4** split is so operators and miners know the **draw is mixed**, not uniformly “toy” or uniformly “olympiad.”

## One way to read the subnet

A useful framing is: **under a fixed validator timeout and a shared, deterministic family of challenges, do prover systems get better over time at producing checkable Lean (and clear reasoning traces) before the window closes?** Lean gives a **ground-truth** pass/fail; the rubric and Pareto token layer compare **how** miners explain their work. Improving on that axis is **exactly** “better at solving (or at least **closing** with a proof) within the allowed wall clock,” not a separate hand-graded exam.

## How miner weights work each epoch (simple)

Think **“fresh contest each round,”** not a bank balance that goes up and down.

1. **One challenge per epoch.** You answer in time (within **`DENDRITE_TIMEOUT_S`**) with a real proof, or that round you’re out of the running for Lean-based rewards from that validator.
2. **Lean must build.** If your proof doesn’t check, you **don’t** get a judge score this epoch.
3. **If Lean passes,** the judge grades **how well you explained** your work. Among successful miners, Lemma ranks **better explanation** and **shorter traces** (Pareto layers — see [`lemma/scoring/pareto.py`](../lemma/scoring/pareto.py)) and turns that into **weights for this round only**.

There is **no** “minus points from last week” counter inside Lemma. A bad round simply means **no (or low) weight from that validator this epoch**. What happens **on-chain** is separate: validators submit **weights**; the chain runs **[Yuma Consensus](https://learnbittensor.org/concepts/scoring-rewards/yuma-consensus)** to agree on how **subnet emissions** are split. Miners on a subnet earn **ALPHA** (the subnet token), not “TAO salary” — see **[Emissions](https://learnbittensor.org/concepts/tokenomics/emissions)** and **[Weights](https://learnbittensor.org/concepts/scoring-rewards/weights)** on Learn Bittensor. **Dynamic TAO (dTAO)** is the economic layer where **TAO** and subnet **ALPHA** interact via **subnet pools** — overview: **[Dynamic TAO](https://learnbittensor.org/concepts/dynamic-tao/subnet-pool)** (and the [Bittensor docs home](https://docs.learnbittensor.org/)). For the short Lemma-specific scoring story, see [FAQ.md](FAQ.md) (“How does scoring work?”).

### Concrete example (one Lemma epoch, one validator)

Numbers are **illustrative**; real splits come from the judge rubric + Pareto math in code.

| UID | What happened | In Lemma’s scoring this epoch |
|-----|----------------|-------------------------------|
| 7 | HTTP timeout (slow miner / dead axon) | **Dropped** before Lean — **no weight** from this validator. |
| 12 | Replied in time, but `lake build` fails | **Dropped** — **no weight**. |
| 3 | Lean passes; judge likes the trace (high rubric score); reasoning text is long | Enters the **Pareto pool** (competes with others who passed). |
| 9 | Lean passes; judge score slightly lower but **much shorter** trace | Also in the **Pareto pool** — might beat UID 3 on the token-efficiency axis. |

The validator builds **`ScoredEntry`** rows only for **3** and **9**, runs **`pareto_weights`**, gets something like **`{3: 0.42, 9: 0.58}`** (hypothetical normalized shares among **this epoch’s survivors**). It then **`set_weights`** on-chain: almost all UIDs get **0**, while **3** and **9** get positive fractions of that validator’s weight vector for that step.

**Two timescales:** Lemma’s **round** is discrete (this epoch’s winners/losers). The **chain** still emits **ALPHA continuously** over blocks: emissions reflect **ongoing consensus** built from **many** validator **`set_weights`** updates over time ([Emissions](https://learnbittensor.org/concepts/tokenomics/emissions)). So miners experience **steady flows** proportional to how **recent** weight consensus favors them — not a single lump sum “when the theorem ends.” Poor rounds **reduce your share of that stream** going forward as weights update; they are not a separate “karma debt” stored inside Lemma.

**Rough intuition (not literal chain math):** imagine your **share** of subnet emissions drifting like **“5% → 5.5% after a strong round → 4.5% after a weak one.”** The mechanism is **updated weight consensus** across validators ([Yuma Consensus](https://learnbittensor.org/concepts/scoring-rewards/yuma-consensus)), not Lemma storing a single **score out of 100** — but the **feel** of an **ongoing percentage that moves** round after round is right.

**Next epoch:** new block ⇒ often a **new theorem**. UID **12** might submit a perfect proof and capture weight then — Lemma **does not** carry over “you failed last time.” Long-run **ALPHA** still comes from **[Yuma Consensus](https://learnbittensor.org/concepts/scoring-rewards/yuma-consensus)** blending **all** validators’ submissions — see Learn Bittensor **[Weights](https://learnbittensor.org/concepts/scoring-rewards/weights)**.

For governance and template upgrades, see [GOVERNANCE.md](GOVERNANCE.md) (generated registry hash). For catalog mode instead of generated, see [CATALOG_SOURCES.md](CATALOG_SOURCES.md).
