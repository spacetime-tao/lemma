# Lemma — consolidated audit remediation tracker

**Purpose:** Single place to track **everything called out** in external reviews (notably **Round 3**, Maciej / Spacetime, post attest + commit-reveal + judge-profile quorum) plus adjacent items from `knowledge/` alignment checks. This is a **backlog and decision log**, not a promise that every line will ship.

**Source text:** The tracker below synthesizes the **full** Round 3 audit (Part 1 incentive layer + Part 2 bloat + §17 KB scorecard + §18 structural redesign + §19 closing). Keep a PDF/markdown copy of the original alongside internal reviews if you need verbatim `file:line` citations (line numbers drift with commits).

**How to use**

- Work **one vertical slice** at a time (fix + test + doc); avoid “implement the whole audit” in one PR.
- Mark rows with status: `open` | `partial` | `done` | `wontfix` | `needs-design`.
- **Mechanism** items (what we measure) require **product/architecture** ownership; **plumbing** items (bugs, consistency, DX) are usual engineering.

**Related:** [incentive-roadmap.md](incentive-roadmap.md), [incentive_migration.md](incentive_migration.md), [training_export.md](training_export.md), `knowledge/INDEX.yaml`.

---

## 1. Executive summary — buckets of work

| Bucket | Nature | Examples |
|--------|--------|----------|
| **A. Objective / economics** | Redesign or explicit acceptance | LLM judge vs kernel ground truth; sybil vs coldkey dedup; Pareto + dedup evasion |
| **B. Consensus & integrity** | Engineering + policy | Body-hash fail-open; deadline `None`; template/registry drift |
| **C. Protocol layers** | Fix bugs vs delete feature | Attest binding; spot-verify predictability; commit-reveal semantics + cache; judge-profile quorum trust model |
| **D. Scoring heuristics** | Iterate under constraint | `proof_intrinsic` padding; comment strip limits; FakeJudge leak |
| **E. Operator / pinning** | Config + docs | Defaults vs “canonical” docs; cross-validator agreement |
| **F. Surface / DX** | Refactor when budget allows | CLI size, duplicate dry-runs, argv hacks |

---

## 2. Priority legend

| Priority | Meaning |
|----------|---------|
| **P0** | Correctness / consensus / silent disagreement risk |
| **P1** | Security-adjacent or clear exploit path under stated threat model |
| **P2** | Incentive distortion but needs design input |
| **P3** | Hardening, ops pain, or debt |
| **P4** | Structural redesign candidates (major release / fork) |

---

## 2a. Round 3 author — highest-leverage moves (ordered)

From audit §19 — **not all are agreed team policy**; use as a prioritized debate list.

1. Delete or replace **`proof_intrinsic_score`** (elaborator-backed metric vs length heuristic). **Partial:** default weight lowered; compare-only Lean metrics added.
2. Decide **`LEMMA_REPUTATION_CREDIBILITY_EXPONENT`** default vs KB **2.5** target. **Done:** divergence documented; default remains `1.0` until governed.
3. **Expand `judge_profile_sha256`** (or sibling hash) to cover subnet-critical knobs currently outside the pin (~18 fields in Round 3). **Done.**
4. **Fail closed** when `computed_body_hash` missing — remove fail-open in `synapse_miner_response_integrity_ok`; update/remove tests that codify bypass. **Done.**
5. **Per-validator salt** in attest spot-verify selection hash (reduces predictable skip + UID grinding). **Done/partial:** salt shipped; residual UID-grinding economics remain design-level.
6. **Sybil / Pareto:** move beyond coldkey dedup toward mechanism aligned with Affine-style winners-take-all-per-subset (needs design). **Bounded next step:** [sybil_economics.md](sybil_economics.md) now requires a replay/economics decision gate before reward-code changes; replay tooling exists, but real export data + governance are still required.
7. Drop **`LEMMA_PROBLEM_SOURCE=frozen`** / bundled JSON if policy allows (large policy decision). **Partial:** direct frozen use is dev-gated.
8. **Aggressively cut CLI / wizard / `main.py` surface** (Part 2 scale stats). **Mostly done:** friendly UX moved to `lemma-cli`, core keeps shims/minimal commands.
9. Move **`lemma/catalog/`** dev tooling to `tools/` (audit flagged twice). **Done.**
10. **Plan structural redesign** — container-based miner artifact + kernel-only scoring (see §12); drops judge stack.

---

## 3. Integrity, transport, and “fail open” behavior

| ID | Issue | Source § | Priority | Remediation direction | Key refs (verify in tree) |
|----|--------|----------|----------|------------------------|---------------------------|
| **I1** | `synapse_miner_response_integrity_ok` returns **True** when `computed_body_hash` is missing → middleboxes can strip headers; combined with attest/trace concerns | R3 §3.1, §6 | P1 | **Done:** miner responses fail closed when `computed_body_hash` is missing or mismatched. | `lemma/protocol.py`, `tests/test_protocol.py` |
| **I2** | `deadline_block is None` may bypass deadline path if fields stripped | R3 §6 | P1 | **Done:** the same integrity gate rejects miner responses without `deadline_block`. | `lemma/protocol.py`, `tests/test_protocol.py`, `lemma/validator/epoch.py` |
| **I3** | Single `block_after_query` for batch — timing games | R3 §6 | P2 | **Done/documented acceptance:** Dendrite exposes a batch result, not a trusted per-response receipt block; validator enforces deadline at the post-batch chain head. | `epoch.py` |
| **I4** | Synapse transport deprecated in KB vs Epistula | R3 §5.15, §11 | P4 | Track `knowledge/` transport migration; out of scope for “quick fix” | `protocol.py`, `knowledge/` |

**2026-05 progress:** I1/I2/I3 patched or bounded. `synapse_miner_response_integrity_ok` now fails closed when `computed_body_hash` is missing, mismatched, or when `deadline_block` is missing from the miner response. Deadline enforcement uses the post-batch chain head because Dendrite does not expose a trusted per-response receipt block.

---

## 4. Scoring objective — “measures the wrong thing”

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **O1** | Rank mixes kernel-verifiable proof with **LLM judge** on miner prose; lowering proof weight to default `w=0.10` reduces text-heuristic padding risk but leaves judge dominance explicit | R3 §2, §11 | P4 / product | **Decision boundary documented:** judge is bootstrap by default unless governance chooses permanent explanation-quality incentives; next scoring change must choose permanent judge, capped/bootstrap judge, or judge-free mode using the decision-record template ([judge-incentive-decision.md](judge-incentive-decision.md)). |
| **O2** | `primary_design_axis` / one-sentence rule in KB violated by current honest description | R3 §2.3 | P4 | **Done/bounded:** current objective pinned as Lean-valid theorem proving; judged reasoning documented as a bootstrap ranking layer, not the default identity of the subnet ([objective-decision.md](objective-decision.md)). |
| **O3** | Pareto + coldkey dedup + identical dedup still allow sybil farming per R3 math | R3 §2.2, §8, §12 | P2/P4 | **Needs-design:** economic modeling; not fixable by parser alone. [sybil_economics.md](sybil_economics.md) records the minimum replay/economics gate; `tools/sybil_replay_analyze.py` provides offline replay summaries from private full exports. |

---

## 5. `proof_intrinsic` — residual gaming

**Decision note:** [proof-intrinsic-decision.md](proof-intrinsic-decision.md) records the current stance: keep the heuristic only as a low-weight bootstrap signal, do not raise its default weight, and do not add more regex padding detectors as the main fix. Default `LEMMA_SCORE_PROOF_WEIGHT` is now `0.10`; comment-only / blank-line padding is normalized out; `LEMMA_LEAN_PROOF_METRICS=1` enables a compare-only Lean probe in `VerifyResult` with byte/line and delimiter-shape metrics. The analyzer now surfaces low-judge / high-metric candidates, data-readiness blockers, and an explicit conservative gate verdict before any scoring change.

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **P1** | Comment stripping defeats **one** padding class; **string literals**, trivial `have … by trivial`, long names still inflate | R3 §2.1 | P2 | Default weight lowered; comment-only / blank-line padding normalized; compare-only Lean probe + v2 calibration added; analyzer now flags low-judge / high-metric candidates and prints a conservative gate verdict. Next real fix must pass the replace / keep-low / remove-reduce decision gate before scoring use. | `lemma/scoring/proof_intrinsic.py`, `config.py`, `docs/proof-intrinsic-decision.md` |
| **P2** | Default credibility exponent `1.0` vs KB mention of `2.5` | R3 §7 | P3 | **Done:** documented divergence; keep `1.0` default until calibrated/governed. Operators can explicitly set `2.5`. | `config.py`, `scoring/reputation.py`, `docs/credibility-exponent-decision.md` |
| **P3** | Credibility rises on Lean pass; padding that passes Lean **does not** get penalized by cred | R3 §7 | P2 | **Done:** accepted as policy boundary. Credibility is Lean pass/fail reliability; padding research stays in compare-only proof metrics until a proof-side scoring replacement is calibrated. | `docs/proof-intrinsic-decision.md`, `docs/credibility-exponent-decision.md` |
| **P4** | Spot-verify skip returns pass → cred EMA increases without verify | R3 §3.2, §7 | P1 | **Done:** attest-trusted skips remain scoreable but no longer improve verify credibility. | `lemma/validator/epoch.py`, `lemma/protocol_attest.py`, `tests/test_reputation.py` |

---

## 6. Miner verify attestation (`protocol_attest`)

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **A1** | Attest preimage does not bind **reasoning** (judge axis); trace swap vs body_hash story | R3 §3.1 | P2 | **Done:** documented as intentional boundary; attest covers proof-local Lean verification, while body hash / commit-reveal bind wider payloads. | `docs/miner-verify-attest.md` |
| **A2** | No validator hotkey in attest; cross-validator replay | R3 §3.1 | P2 | **Done:** v2 attest preimage binds validator hotkey. | `lemma/protocol_attest.py`, `tests/test_protocol_attest.py` |
| **A3** | Spot fraction `<1` → predictable selection; no per-validator salt; UID grinding | R3 §3.2 | P1 | **Done/partial:** salted selection and credibility split shipped; residual UID-grinding economics stay design-level. | `lemma/protocol_attest.py`, `docs/miner-verify-attest.md` |
| **A4** | On spot skip, theorem/proof mismatch not caught by verify | R3 §3.3 | P1 | **Done:** validator rejects responses whose challenge fields do not match the current theorem/metronome before attest trust or scoring. | `lemma/validator/epoch.py`, `tests/test_validator_challenge_binding.py` |
| **A5** | “TEE” naming vs actual user-space Docker attest | R3 §3.4 | P3 | **Done:** docs state miner verify attest is a hotkey signature over a local Lean claim, not hardware remote attestation. | `docs/miner-verify-attest.md` |

**2026-05 progress:** A1/A2/A3/A4/A5 and P4 patched/documented: attest-trusted spot skips remain scoreable, but no longer improve verify credibility. Credibility only increases from validator Lean verification; full-verify failures still lower it. Spot selection now accepts `LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT`; `judge_profile_sha256` pins its SHA-256 without exposing the salt. Validators reject responses whose theorem, challenge source, toolchain pins, metronome id, or deadline block do not match the current challenge before attest trust or scoring. The v2 attest preimage binds validator hotkey, theorem, metronome, toolchain pins, and proof hash, and [miner-verify-attest.md](miner-verify-attest.md) records the non-TEE threat model.

---

## 7. Commit–reveal

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **C1** | Two phases **same validator process**, no chain delay — may not match threat model that CR usually assumes | R3 §4 | P4 | **Done:** threat model documented; commit-reveal is optional same-round payload binding, not chain-anchored public fairness. | `docs/commit-reveal.md` |
| **C2** | Miner `forward.py` cache **no eviction** — memory growth | R3 §4.1 | P1 | **Done:** cache entries have TTL and max-entry pruning. | `lemma/miner/forward.py`, `tests/test_miner_commit_reveal.py` |
| **C3** | Cache key `(theorem_id, metronome_id)` → cross-validator overwrite | R3 §4.2 | P1 | **Done:** cache key includes validator dendrite hotkey. | `lemma/miner/forward.py`, `tests/test_miner_commit_reveal.py` |
| **C4** | `looks_like_commitment_hex` vs `0x` — regex strict; reveal path strips `0x` | R3 §4.3 | P2 | **Done:** commitment hex normalization accepts optional `0x` consistently. | `lemma/protocol_commit_reveal.py`, `lemma/validator/epoch.py`, `lemma/miner/forward.py` |
| **C5** | `json.dumps(..., sort_keys=True)` on **list** in `reasoning_blob_for_commit` — meaningless flag | R3 §4.4 | P3 | **Done:** removed the no-op list `sort_keys` argument. | `lemma/protocol_commit_reveal.py` |

**2026-05 progress:** C1/C2/C3/C4/C5 patched for the usable commit-reveal path: miner commit cache is TTL/max-entry bounded, cache keys include validator dendrite hotkey, commitment hex accepts optional `0x`, the no-op `sort_keys=True` was removed from list serialization, and [commit-reveal.md](commit-reveal.md) records the limited same-round threat model.

---

## 8. Judge profile peer quorum

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **J1** | HTTP plaintext / no auth; MITM | R3 §5.1 | P2 | **Done:** documented as operator-controlled transport; use TLS/private network/auth outside this helper. |
| **J2** | All-of-N flaky; no Byzantine resistance | R3 §5.1 | P2 | **Done:** documented current all-of-N behavior and non-Byzantine limits; stronger k-of-n/on-chain design deferred. |
| **J3** | Hash omits many subnet-critical env vars | R3 §5.3 | P2 | **Done:** profile hash broadened into validator scoring profile. |
| **J4** | `LEMMA_JUDGE_PROFILE_ATTEST_SKIP` foot-gun | R3 §5.1 | P3 | **Done:** docs and validator-check wording label skip as solo/dev only, not production alignment. |

**2026-05 progress:** J1/J2/J3/J4 patched/documented. `judge_profile_sha256` is now a validator scoring profile covering judge stack, deterministic problem cadence, verification timeout/image policy, scoring blend/dedup/reputation settings, and protocol hooks that affect response acceptance. [judge-profile-attest.md](judge-profile-attest.md) records the HTTP peer check as operator coordination, not Byzantine consensus or transport security.

---

## 9. Judge JSON / prompt / FakeJudge

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **G1** | **Dedupe** of identical dicts across parse passes → **echo** rubric may collapse to one valid score | R3 §10.1 | P2 | **Done:** parser now rejects repeated valid rubric occurrences even when values are identical; tests cover echoed fenced rubric + final rubric. | `lemma/judge/json_util.py`, `tests/test_judge_json.py` |
| **G2** | Two **distinct** valid rubrics in trace → parse fails → miner dropped | R3 §10.1 | P2 | **Done:** fail-closed policy pinned; exactly one valid rubric object is required, while wrong-shaped junk JSON can be skipped before a later valid rubric. | `lemma/judge/json_util.py`, `tests/test_judge_json.py` |
| **G3** | Sanitizer only escapes ``` ; many other injection channels | R3 §10.2–10.3 | P2 | **Done/partial:** prompt fences miner text, breaks triple-backtick fence escapes, and tells judge to ignore instructions/JSON inside fences; determined model-side injection remains model-dependent. | `lemma/judge/prompt_sanitize.py`, `lemma/judge/prompts.py`, `tests/test_prompt_sanitize.py` |
| **G4** | **FakeJudge** length curve; missing API key falls back with log only | R3 §10.4 | P1 | **Done:** live validator rejects FakeJudge / missing judge credentials; dry-run keeps explicit FakeJudge behavior. | `lemma/validator/epoch.py`, `lemma/common/config.py`, `tests/test_validator_judge_strict.py`, `tests/test_validator_build_judge.py` |

**2026-05 progress:** G1/G2/G3/G4 patched/documented. Judge parsing is fail-closed around valid rubric multiplicity, including identical repeated rubric objects; invalid dict-shaped junk can be skipped so a later single valid rubric can win. Miner-controlled theorem, trace, and proof are fenced before judge calls, triple-backtick escapes are broken, and the prompt tells the model to ignore instructions/JSON inside those fences. Live validator epochs now raise when judge API keys are missing or `LEMMA_FAKE_JUDGE` is forced; dry-run still uses FakeJudge by default.

---

## 10. Problem supply — templates, seed, frozen

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **R1** | Small generated template set is enumerable; SHA256 mix is **public** — offline cache still works | R3 §9, §9.1 | P2 | **Needs-design/partial:** public deterministic supply boundary documented; current registry expanded from 28 to 40 builders; mitigation is builder breadth, explicit release rotation, and future curated lanes, not seed secrecy. | `docs/problem-supply-policy.md`, `docs/generated-problems.md` |
| **R2** | `generated_registry_sha256` may not hash builder **bodies** — skew risk | R3 §9.3 | P0/P1 | **Done:** registry fingerprint includes builder source hashes. | `lemma/problems/generated.py`, `tests/test_registry_fingerprint.py` |
| **R3** | `RNG_MIX_TAG` not in registry pin | R3 §9.3 | P1 | **Done:** registry fingerprint includes `RNG_MIX_TAG`. | `lemma/problems/generated.py`, `tests/test_registry_fingerprint.py` |
| **R4** | Frozen miniF2F route / gate consistency | R3 §9.2 | P1 | **Done:** `resolve_problem` now gates direct frozen catalog ids behind `LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`, matching `get_problem_source` / validator-check policy. | `problems/factory.py`, `tests/test_problem_factory.py` |
| **R5** | Hardcoded toolchain / mathlib / sandbox `:latest` etc. | R3 §13 | P3 | **Done:** local `:latest` documented as dev-only; production pin policy added for immutable sandbox refs. | `docs/toolchain-image-policy.md`, `.env.example`, `docs/production.md` |

**2026-05 progress:** R1/R2/R3/R4/R5 patched or bounded. The public deterministic problem-supply boundary is documented in [problem-supply-policy.md](problem-supply-policy.md); this does not solve finite template predictability, but it prevents SHA mixing from being misdescribed as secrecy. The generated-registry fingerprint now includes `RNG_MIX_TAG`, builder count/split metadata, and a source hash for each builder function. Direct frozen catalog ids now require `LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`, matching `get_problem_source` and validator-check policy. Sandbox image policy now treats `lemma/lean-sandbox:latest` as a local dev tag and production `LEAN_SANDBOX_IMAGE` as an immutable operator-published ref. `docs/generated-problems.md` reflects the live 40-builder mix.

---

## 11. Dedup & sybil

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **D1** | Coldkey dedup ≠ sybil resistance per KB | R3 §8 | P4 | **Done/bounded:** documented as anti-clutter only; economic mitigations stay outside default code until the decision gate passes. |
| **D2** | Identical dedup bypass via whitespace / comments / trace | R3 §8 | P2 | **Partial:** fingerprint now strips proof comments and collapses whitespace in theorem/proof/trace. Semantic trace rewrites remain a design/economics issue. |

---

## 12. Structural options (not a single ticket)

Round 3 §11 and §18 propose a **minimum-viable direction** under `knowledge/`: hybrid **`container_execution` + `adversarial_red_blue`**, Docker image commitment on-chain, Lean kernel as sole rubric, ε-Pareto over `(passed, latency, proof bytes)` across environment subsets, **no LLM judge**. That implies deleting large swaths of today’s stack (`lemma/miner/` reference path, judge, much protocol glue) — **program-level fork**, not a sprint.

Track exploration separately from **incremental** rows in §3–§11.

---

## 13. Part 2 — Bloat, redundancy, dead weight (Round 3 §14–16)

Treat as **P3** debt unless an item is safety-critical (called out inline).

### 13.1 Scale snapshot (author metrics — rerun `wc` / `tokei` periodically)

Current snapshot uses `wc -l` over Python files, except `docs/` which counts Markdown lines. This is a blunt maintenance-load measure, not semantic code complexity.

| Layer | Round 3 cited LoC | 2026-05 current `wc -l` | Delta |
|-------|-------------------|-------------------------|-------|
| `lemma/cli/` | 5 398 (16 files) | 1 820 (6 files) | -3 578 |
| `lemma/validator/` | 875 | 1 142 | +267 |
| `lemma/scoring/` | 282 | 305 | +23 |
| `lemma/judge/` | 543 | 568 | +25 |
| `lemma/lean/` | 1 117 | 1 260 | +143 |
| `lemma/miner/` | 1 082 | 1 075 | -7 |
| `lemma/problems/` | 784 | 1 004 | +220 |
| `lemma/protocol*` | 290 | 331 | +41 |
| `lemma/common/` | 1 110 | 1 285 | +175 |
| `lemma/` total | **12 630** | **8 826** (66 files) | **-3 804** |
| `tests/` | 2 330 | 3 859 (59 files) | +1 529 |
| `docs/` markdown | 1 355 | 2 810 (30 files) | +1 455 |

CLI alone was cited as **43 %** of `lemma/`; it is now about **21 %** by this simple line-count snapshot. The core shrank substantially, while tests/docs grew because safety gates, replay guards, and decision records were added.

### 13.2 CLI / click surface (§15–16)

- **Dry-run surface** — duplicate aliases (`miner --dry-run`, `miner-dry`, `validator --dry-run`, `validator-dry`) removed; canonical commands are `lemma miner dry-run`, `lemma validator dry-run`, and `lemma validator config`.
- **Argv hack:** `_rewrite_lemma_argv_numeric_menu` + `_LEMMA_QUICK_MENU_EXTRAS_JSON` mutated `sys.argv` on import (`main.py`); removed in the first CLI extraction trim.
- **`uv_bootstrap.py`** + tests vs documenting `uv run`; removed from core.
- **`interactive_venv_shell.py`** (~176 LoC) vs one-line `source .venv`; removed in the first CLI extraction trim.
- **`_looks_like_shell_step`** frozenset — partial shell interception.
- **`leaderboard_cmd`** wrapped metagraph display already available through `btcli subnet show`; removed from core. **`miner_menu` / `validator_menu`** duplicated subcommands and were removed in the first CLI extraction trim.
- **`docs/` opener** + `_DOCS_BY_SLUG` hardcoded tuple moved to `lemma-cli`; core keeps a redirect only.
- **`configure` ×8** near-identical subcommands moved to `lemma-cli`; core keeps redirect shims only.
- **`try_prover.py`** (~677 LoC) local operator preview moved to `lemma-cli`; core keeps redirects only.
- **`start_screen.py`** (~569 LoC) single mega-menu; removed in the first CLI extraction trim.
- **`glossary.py`** moved to `lemma-cli`; core keeps a redirect only.
- **`doctor`** moved to `lemma-cli`; core keeps a redirect only.
- **`miner observability`** moved to `lemma-cli miner-observability`; core keeps a redirect only.
- **`bittensor[cli]`** moved behind optional `btcli` extra; core depends on the Bittensor SDK only, while operators can still run `uv sync --extra btcli` for wallet/register commands.
- **`validator-check` interactive start prompt** removed; core pre-flight now exits after READY / NOT READY, while guided handoff belongs in `lemma-cli`.
- **`local-loop`** undocumented FakeJudge + host-Lean dev shortcut removed; use explicit `lemma validator dry-run` or `lemma-cli rehearsal` instead.
- **Moved-command redirects** now share one tiny registration helper instead of one wrapper function per friendly command.

Extraction note: `lemma-cli` now owns the friendly `start` surface; the core repo keeps only a small compatibility hint and explicit miner/validator subcommands.

### 13.3 Protocol & glue

- **`protocol_attest`**: redundant length check after fixed-length signature decode removed.
- **`protocol_commit_reveal`**: duplicate strip/length pattern consolidated into shared hex helpers; commit and reveal paths accept optional `0x` consistently.
- **`epoch._verify_one`**: verify batch now uses `return_exceptions=True`; one UID verifier exception drops that UID instead of the whole batch. Defaulted kwargs remain as local task captures.
- **`validator/protocol_migration.py`** no-op removed; validator startup now checks live settings directly.
- **`validator-check` vs `ValidatorService` startup gates** now share one readiness helper for Docker mode, judge stack policy, judge key, pins, generated registry hash, frozen-source gate, and judge-profile peer attest.
- **`validator/query.py`** thin wrapper removed; epoch calls `bt.Dendrite` directly.
- **`common/uids.py`** single-use axon-list wrapper removed; epoch reads metagraph axons directly.
- **`common/split_timeout.py`** single-use split multiplier removed; epoch keeps the tiny mapping inline.
- **`miner/__init__.py` / `validator/__init__.py`** no longer re-export service classes on package import.
- **`judge/__init__.py`** no longer re-exports judge classes on package import; callers import concrete modules.
- **`lean/__init__.py` / `problems/__init__.py` / `reasoning/__init__.py`** no longer re-export internals on package import.
- **`reputation.apply_ema_to_entries`**: third return element discarded; removed from API.
- **`scoring/dedup.py`**: parallel `dedup_identical` / `dedup_coldkeys` now share one internal best-by-key helper.
- **`scoring/__init__.py`**: unused convenience re-exports removed; callers import concrete scoring modules directly.
- **Style proliferation:** mixed dataclass / pydantic / hand JSON (`ScoredEntry`, `RubricScore`, …).
- **`ScoredEntry.composite` vs `reasoning_score`**: duplicate identity removed; `ScoredEntry` keeps `reasoning_score` only.
- **`tokens.py` / tiktoken:** removed; rewards use deterministic `len(trace)` directly for the Pareto trace-length axis.
- **`mix_sub_problem_seed` multi-round path:** kept intentionally for optional `LEMMA_EPOCH_PROBLEM_COUNT` > 1; config is bounded, profile-pinned, documented, and covered by a deterministic seed test.

### 13.4 Lean sandbox

- Three execution paths (one-shot Docker, exec worker, host `lake`).
- Host-before-Docker Lake prefetch removed; cache-get remains only in the active host verify or networked Docker workspace.
- **`_clone_dot_lake`** removed; first passing verify publishes the whole workspace by same-directory rename.
- **`_template_slot_lock`** LRU in-process only.
- **`_publish_workspace_cache`** simplified to one locked same-directory rename into an empty cache slot.
- Warm Lake-cache behavior now has one override: `LEMMA_LEAN_ALWAYS_CACHE_GET=1` forces `lake exe cache get`; otherwise warm `.lake/packages/mathlib` workspaces skip it.
- **HTTP worker** subsystem optional (~250 LoC) — topology docs “advanced.”
- Duplicate `r.returncode` branches in `_verify_host` removed; local double cheat scan removed (remote pre-scan retained before POST).
- Docker verify script now writes a workspace script and invokes Docker with argv/workdir instead of a quoted `bash -lc` command string.
- Default-off comparator hook removed from the verifier; external comparator experiments should live outside core scoring until there is a pinned subnet policy.

### 13.5 Miner

- **`PROVER_SYSTEM`** slimmed from a long reference-spec prompt to a focused JSON / reasoning / Lean contract.
- Duplicated OpenAI vs Anthropic branches in prover — shared solve/log/parse flow extracted; provider-specific
  HTTP calls remain separate.
- Four orthogonal observability toggles → log shape explosion — documented uppercase env names remain;
  undocumented lowercase env aliases for miner log toggles were removed.
- **`daily_budget`** JSON persistence kept intentionally as an off-by-default API-spend guard.
- **`public_ip.py`** third-party calls — public IP discovery is now opt-in (`AXON_DISCOVER_EXTERNAL_IP=true`);
  production miners should set `AXON_EXTERNAL_IP` explicitly.
- **`model_card_text`** removed from the built-in miner; `model_card` remains optional protocol/export metadata.
- **`_stats` / `_commit_reveal_cache`** globals in forward handler — done: miner summary stats and commit-reveal
  cache state are now scoped to the `make_forward` handler instance; the cache remains TTL/max-entry bounded and
  validator-keyed.
- Miner default priority stub removed; the no-op default now lives directly at the service callsite.
- Stub proof for `two_plus_two` in production path per audit — removed; missing prover keys now always return
  the unsolved challenge as a fail-closed stub.
- **`synapse_payload_error` triple invocation** in commit-reveal mode clarified: incoming challenge checks now skip response-only validation; outgoing commit/reveal responses still run response validation.

### 13.6 Configuration (`config.py`)

- File cited ~**980 LoC** — growth without removing scaffolding.
- Large `Field` surface remains, but lower-case field-name env aliases and `AliasChoices` have been removed.
- Triple aliases on several wallet/prover fields.
- **`allow_noncanonical_judge_model`** — removed; it was an ignored compatibility knob and did not affect validator judge policy.
- Resolver collapse opportunities (`anthropic` vs OpenAI keys) — validator pre-flight now follows the single
  Chutes-compatible key path; OpenAI-compatible judge/prover key resolvers trim consistently.
- **`validator_judge_stack_strict`** vs unreachable Anthropic judge branch on validator — Anthropic branch removed from validator epoch builder; local one-shot judge tooling remains.
- Six env names for two wallet values — validator wallet overrides now keep the documented
  `BT_VALIDATOR_WALLET_COLD` / `BT_VALIDATOR_WALLET_HOT` env names and drop the unused `LEMMA_*` aliases.
- Reserved protocol toggles default **False** but many Fields persist — documented `LEMMA_*` env names remain;
  undocumented lowercase env aliases were removed from the commit-reveal, miner-attest, and judge-attest switches.
- Timeout-split / prover self-rejection knobs — documented uppercase env names remain; undocumented lowercase
  env aliases were removed. Timeout-split stays validator policy; prover minimums stay miner-only retry policy.
- Settings env aliases now accept documented uppercase names only; lowercase field-name env aliases were removed
  while Python constructor kwargs remain available through an init-time alias shim.

### 13.7 Tests (coverage imbalance)

- ~**20 %** mechanism math tests vs **~40 %** protocol vs **~42 %** glue vs **~7 %** pure CLI — author breakdown; periodically recompute.
- Tests called out as low value: `uv_bootstrap` (removed), `try_prover` flag tables (moved to `lemma-cli`), `problem_views` title case (removed), `protocol_migration` no-op test (removed), body-hash fail-open expectations in `test_protocol.py` (replaced with fail-closed coverage), thin `prompt_sanitize` coverage.
- **`tests/test_rewards.py`** added for **`entry_from_scores`** / rewards assembly.

### 13.8 Catalog (`lemma/catalog/`)

- ~388 LoC; production cited as **`catalog/constants.py` only** — builder/parser helpers moved to `tools/catalog`; runtime `lemma/catalog` now keeps constants only.

### 13.9 Repository-root / misc

- Root **`validator.py`** stub removed; docs point to `lemma validator start`.
- **`voibes.jpeg`** unused asset removed.
- **`env.example`** removed; **`.env.example`** is the only env template.
- **`scripts/load_minif2f.py`** removed; `scripts/build_lemma_catalog.py` is the single catalog rebuild path.
- **`scripts/lemma-run`** removed; docs use standard `uv run` commands instead of a repo wrapper.
- **`examples/legacy_subnet_burn_validator.py`** removed; it was not a Lemma validator and set 100% weight to UID 0.
- **`docs/comparator.md`** and runtime comparator hook removed; no bundled production comparator or unpinned post-verify command path.
- **`pyproject.toml` extras** — `tiktoken` removed; `anthropic` and `btcli` moved to optional extras.
- **`Dockerfile`** no longer installs full `docker.io`; runtime image uses Python Docker SDK + mounted host socket. Added `.dockerignore`.

---

## 14. Knowledge-base contract scorecard (Round 3 §17)

Abbreviated; see `knowledge/` for full YAML. Status reflects the current remediation state against the Round 3 narrative; major mechanism rows still need design review before becoming gates.

| Invariant | KB pointer | Current remediation status |
|-----------|------------|----------------------|
| One-sentence primary design axis | `subnet.invariants.yaml` | Current objective pinned in `docs/objective-decision.md`; judge layer bounded separately |
| Validator-only development | `subnet.invariants.yaml#architecture.validator_only_development` | Still violated by bundled reference miner; `PROVER_SYSTEM` is slimmed but still present |
| Single-file validator pattern | `validator.contract.yaml` | Still violated by package layout; root `validator.py` stub removed |
| Push compute to miners | `subnet.invariants.yaml#compute_distribution` | Still violated |
| EMA for stability | `validator.rules.yaml` | Honored |
| Credibility tracking tuning | `incentive.primitives.yaml` | Wired; default exponent divergence documented in `docs/credibility-exponent-decision.md` |
| Secret eval sets | `validator.rules.yaml` | Still gated; not in judge pin |
| N miners profitability | `sybil.realities.yaml` | Still violated; decision gate and offline replay helper added, real replay data/governance still pending before reward-code changes |
| Coldkey dedup ≠ sybil resistance | `sybil.realities.yaml` | Still violated by design; documented as anti-clutter only |
| Validators not individually trusted | `trust.assumptions.yaml` | Softer-trust model documented for Chutes + voluntary HTTP peer checks |
| Synapse deprecated | `subnet.invariants.yaml` | Still violated |
| Open-source / corpus | `subnet.invariants.yaml` | Partially mitigated (`reasoning_only` export) |
| Hardware attestation | `trust.assumptions.yaml` | Miner verify attest documented as non-TEE hotkey signature over local Lean claim |
| Container / red-blue patterns | `container_execution.yaml`, `adversarial_red_blue.yaml` | Not adopted |
| Commit-reveal when needed | `subnet.invariants.yaml#commit_reveal` | Optional same-round binding documented; not chain-anchored fairness |
| Similarity detection | `validator.rules.yaml` | Partial: exact fingerprint strips proof comments and collapses whitespace; semantic rewrites remain |
| HTTP + Epistula for miners | `miner.contract.yaml` | Not used |

---

## 15. Hardcoded constants checklist (R3 §13)

Use as **release audit**: each row is “pin or document why not pinned.” No code changes required in this doc—track in issues when flipping defaults.

Examples called out in Round 3: judge model/URL, Anthropic default model age, Lean/Mathlib pins, sandbox image tag, `RNG_MIX_TAG`, magic bytes, spot hash width, quorum strictness, proof weight, EMA alphas, forward timeout, **slack blocks**, etc.

---

## 16. Suggested workflow for the team

1. **Triage meeting:** Assign IDs in §3–§11 and bullets in §13 to `open` / `wontfix` / `needs-design` with owner.
2. **Sprint:** Pick **one P0/P1** cluster (e.g. I1+I2, or C3+C2, or G4) **or** one **§2a** item with explicit acceptance criteria.
3. **Exit criteria:** Tests + operator note + update linked issue; bump §17 if scope changes materially.
4. **Avoid:** Treating §12–§14 as single-ticket refactors — sequence or fork explicitly.

---

## 17. Document history

| When | What |
|------|------|
| 2026-05 | Initial consolidation from Round 3 audit narrative + repo pointers |
| 2026-05 | Merged **full** Round 3 Part 2 (§14–16), §17 KB scorecard, §18 pointer, §19 → §2a |
| 2026-05 | Refreshed scorecard after CLI extraction, dedup normalization, and miner prompt trims |
| 2026-05 | Refreshed §13.1 scale snapshot after CLI extraction and cleanup passes |

**Maintainers:** bump §17 when you materially change scope or close a whole section.
