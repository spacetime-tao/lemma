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
6. **Sybil / Pareto:** move beyond coldkey dedup toward mechanism aligned with Affine-style winners-take-all-per-subset (needs design).
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
| **I3** | Single `block_after_query` for batch — timing games | R3 §6 | P2 | Per-response block or documented acceptance | `epoch.py` |
| **I4** | Synapse transport deprecated in KB vs Epistula | R3 §5.15, §11 | P4 | Track `knowledge/` transport migration; out of scope for “quick fix” | `protocol.py`, `knowledge/` |

**2026-05 progress:** I1/I2 patched in `synapse_miner_response_integrity_ok`: validator responses now fail closed when `computed_body_hash` is missing, mismatched, or when `deadline_block` is missing from the miner response.

---

## 4. Scoring objective — “measures the wrong thing”

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **O1** | Rank mixes kernel-verifiable proof with **LLM judge** on miner prose; lowering proof weight to default `w=0.10` reduces text-heuristic padding risk but leaves judge dominance explicit | R3 §2, §11 | P4 / product | **Decision boundary documented:** judge is bootstrap by default unless governance chooses permanent explanation-quality incentives; next scoring change must choose permanent judge, capped/bootstrap judge, or judge-free mode ([judge-incentive-decision.md](judge-incentive-decision.md)). |
| **O2** | `primary_design_axis` / one-sentence rule in KB violated by current honest description | R3 §2.3 | P4 | **Done/bounded:** current objective pinned as Lean-valid theorem proving; judged reasoning documented as a bootstrap ranking layer, not the default identity of the subnet ([objective-decision.md](objective-decision.md)). |
| **O3** | Pareto + coldkey dedup + identical dedup still allow sybil farming per R3 math | R3 §2.2, §8, §12 | P2/P4 | Economic modeling; not fixable by parser alone |

---

## 5. `proof_intrinsic` — residual gaming

**Decision note:** [proof-intrinsic-decision.md](proof-intrinsic-decision.md) records the current stance: keep the heuristic only as a low-weight bootstrap signal, do not raise its default weight, and do not add more regex padding detectors as the main fix. Default `LEMMA_SCORE_PROOF_WEIGHT` is now `0.10`; comment-only / blank-line padding is normalized out; `LEMMA_LEAN_PROOF_METRICS=1` enables a compare-only Lean probe in `VerifyResult`.

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **P1** | Comment stripping defeats **one** padding class; **string literals**, trivial `have … by trivial`, long names still inflate | R3 §2.1 | P2 | Default weight lowered; comment-only / blank-line padding normalized; compare-only Lean probe + initial calibration added. Next real fix must pass the replace / keep-low / remove-reduce decision gate before scoring use. | `lemma/scoring/proof_intrinsic.py`, `config.py`, `docs/proof-intrinsic-decision.md` |
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
| **R1** | Small generated template set is enumerable; SHA256 mix is **public** — offline cache still works | R3 §9, §9.1 | P2 | **Needs-design/partial:** public deterministic supply boundary documented; current registry expanded from 28 to 40 builders; mitigation is builder breadth, release rotation, and future curated lanes, not seed secrecy. | `docs/problem-supply-policy.md`, `docs/generated-problems.md` |
| **R2** | `generated_registry_sha256` may not hash builder **bodies** — skew risk | R3 §9.3 | P0/P1 | **Done:** registry fingerprint includes builder source hashes. | `lemma/problems/generated.py`, `tests/test_registry_fingerprint.py` |
| **R3** | `RNG_MIX_TAG` not in registry pin | R3 §9.3 | P1 | **Done:** registry fingerprint includes `RNG_MIX_TAG`. | `lemma/problems/generated.py`, `tests/test_registry_fingerprint.py` |
| **R4** | Frozen miniF2F route / gate consistency | R3 §9.2 | P1 | **Done:** `resolve_problem` now gates direct frozen catalog ids behind `LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`, matching `get_problem_source` / validator-check policy. | `problems/factory.py`, `tests/test_problem_factory.py` |
| **R5** | Hardcoded toolchain / mathlib / sandbox `:latest` etc. | R3 §13 | P3 | **Done:** local `:latest` documented as dev-only; production pin policy added for immutable sandbox refs. | `docs/toolchain-image-policy.md`, `.env.example`, `docs/production.md` |

**2026-05 progress:** R1/R2/R3/R4/R5 patched or bounded. The public deterministic problem-supply boundary is documented in [problem-supply-policy.md](problem-supply-policy.md); this does not solve finite template predictability, but it prevents SHA mixing from being misdescribed as secrecy. The generated-registry fingerprint now includes `RNG_MIX_TAG`, builder count/split metadata, and a source hash for each builder function. Direct frozen catalog ids now require `LEMMA_DEV_ALLOW_FROZEN_PROBLEM_SOURCE=1`, matching `get_problem_source` and validator-check policy. Sandbox image policy now treats `lemma/lean-sandbox:latest` as a local dev tag and production `LEAN_SANDBOX_IMAGE` as an immutable operator-published ref. `docs/generated-problems.md` reflects the live 40-builder mix.

---

## 11. Dedup & sybil

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **D1** | Coldkey dedup ≠ sybil resistance per KB | R3 §8 | P4 | Document; economic mitigations outside code |
| **D2** | Identical dedup bypass via whitespace / comments / trace | R3 §8 | P2 | Normalize proof bytes if desired; tradeoffs with honest variance |

---

## 12. Structural options (not a single ticket)

Round 3 §11 and §18 propose a **minimum-viable direction** under `knowledge/`: hybrid **`container_execution` + `adversarial_red_blue`**, Docker image commitment on-chain, Lean kernel as sole rubric, ε-Pareto over `(passed, latency, proof bytes)` across environment subsets, **no LLM judge**. That implies deleting large swaths of today’s stack (`lemma/miner/` reference path, judge, much protocol glue) — **program-level fork**, not a sprint.

Track exploration separately from **incremental** rows in §3–§11.

---

## 13. Part 2 — Bloat, redundancy, dead weight (Round 3 §14–16)

Treat as **P3** debt unless an item is safety-critical (called out inline).

### 13.1 Scale snapshot (author metrics — rerun `wc` / `tokei` periodically)

| Layer | Round 3 cited LoC |
|-------|-------------------|
| `lemma/cli/` (16 files) | 5 398 |
| `lemma/validator/` | 875 |
| `lemma/scoring/` | 282 |
| `lemma/judge/` | 543 |
| `lemma/lean/` | 1 117 |
| `lemma/miner/` | 1 082 |
| `lemma/problems/` | 784 |
| `lemma/protocol*` | 290 |
| `lemma/common/` | 1 110 |
| `lemma/` total | **12 630** |
| `tests/` | 2 330 |
| `docs/` markdown | 1 355 |

CLI alone cited as **43 %** of `lemma/` and **83 %** of combined runtime core size — justify ROI before expanding.

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
- **`bittensor[cli]`** moved behind optional `btcli` extra; core depends on the Bittensor SDK only, while operators can still run `uv sync --extra btcli` for wallet/register commands.

Extraction note: `lemma-cli` now owns the friendly `start` surface; the core repo keeps only a small compatibility hint and explicit miner/validator subcommands.

### 13.3 Protocol & glue

- **`protocol_attest`**: redundant length check after fixed-length signature decode removed.
- **`protocol_commit_reveal`**: duplicate strip/length pattern consolidated into shared hex helpers; commit and reveal paths accept optional `0x` consistently.
- **`epoch._verify_one`**: verify batch now uses `return_exceptions=True`; one UID verifier exception drops that UID instead of the whole batch. Defaulted kwargs remain as local task captures.
- **`validator/protocol_migration.py`** no-op removed; validator startup now checks live settings directly.
- **`validator/query.py`** thin wrapper removed; epoch calls `bt.Dendrite` directly.
- **`reputation.apply_ema_to_entries`**: third return element discarded; removed from API.
- **`scoring/dedup.py`**: parallel `dedup_identical` / `dedup_coldkeys` now share one internal best-by-key helper.
- **`scoring/__init__.py`**: unused convenience re-exports removed; callers import concrete scoring modules directly.
- **Style proliferation:** mixed dataclass / pydantic / hand JSON (`ScoredEntry`, `RubricScore`, …).
- **`ScoredEntry.composite` vs `reasoning_score`**: duplicate identity removed; `ScoredEntry` keeps `reasoning_score` only.
- **`tokens.py` / tiktoken:** replaced with deterministic `len(text)` trace-length proxy; dependency removed.
- **`mix_sub_problem_seed` multi-round path:** kept intentionally for optional `LEMMA_EPOCH_PROBLEM_COUNT` > 1; config is bounded, profile-pinned, documented, and covered by a deterministic seed test.

### 13.4 Lean sandbox

- Three execution paths (one-shot Docker, exec worker, host `lake`).
- Three Lake warm / cache-get strategies + env gates.
- **`_clone_dot_lake`** darwin vs linux copy + long timeouts.
- **`_template_slot_lock`** LRU in-process only.
- **`_publish_workspace_cache`** atomic rename story without cross-process guarantee per audit narrative.
- **HTTP worker** subsystem optional (~250 LoC) — topology docs “advanced.”
- Duplicate `r.returncode` branches in `_verify_host`; **double cheat scan** (runner + sandbox).
- **`_docker_verify_inner_script`** bash string concatenation / quoting hazard.
- **`comparator_hook`**: wired but default-off / no production comparator.

### 13.5 Miner

- **`PROVER_SYSTEM`** (~130 lines) — reference-spec liability (`prover.py`).
- Duplicated OpenAI vs Anthropic branches in prover.
- Four orthogonal observability toggles → log shape explosion.
- **`daily_budget`** JSON persistence when enabled.
- **`public_ip.py`** third-party calls.
- **`model_card_text`** — validator does not score it.
- **`_stats` / `_commit_reveal_cache`** globals in forward handler; commit-reveal cache is now TTL/max-entry
  bounded and validator-keyed; miner summary stats are now scoped to the `make_forward` handler instance.
- Stub proof for `two_plus_two` in production path per audit — removed; missing prover keys now always return
  the unsolved challenge as a fail-closed stub.
- **`synapse_payload_error` triple invocation** in commit-reveal mode clarified: incoming challenge checks now skip response-only validation; outgoing commit/reveal responses still run response validation.

### 13.6 Configuration (`config.py`)

- File cited ~**980 LoC** — growth without removing scaffolding.
- **102 `Field` / 102 `AliasChoices`** — lower-case aliases allegedly unused in production.
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

### 13.7 Tests (coverage imbalance)

- ~**20 %** mechanism math tests vs **~40 %** protocol vs **~42 %** glue vs **~7 %** pure CLI — author breakdown; periodically recompute.
- Tests called out as low value: `uv_bootstrap` (removed), `try_prover` flag tables (moved to `lemma-cli`), `problem_views` title case, `protocol_migration` no-op test (removed), body-hash fail-open expectations in `test_protocol.py` (replaced with fail-closed coverage), thin `prompt_sanitize` coverage.
- **`tests/test_rewards.py`** added for **`entry_from_scores`** / rewards assembly.

### 13.8 Catalog (`lemma/catalog/`)

- ~388 LoC; production cited as **`catalog/constants.py` only** — builder/parser helpers moved to `tools/catalog`; runtime `lemma/catalog` now keeps constants only.

### 13.9 Repository-root / misc

- Root **`validator.py`** stub removed; docs point to `lemma validator start`.
- **`voibes.jpeg`** unused asset removed.
- **`env.example`** removed; **`.env.example`** is the only env template.
- **`scripts/load_minif2f.py`** removed; `scripts/build_lemma_catalog.py` is the single catalog rebuild path.
- **`scripts/lemma-run`** removed; docs use standard `uv run` commands instead of a repo wrapper.
- **`docs/comparator.md`** clarified as experimental/default-off; no bundled production comparator or profile pin.
- **`pyproject.toml` extras** — `tiktoken` removed; `anthropic` and `btcli` moved to optional extras.
- **`Dockerfile`** no longer installs full `docker.io`; runtime image uses Python Docker SDK + mounted host socket. Added `.dockerignore`.

---

## 14. Knowledge-base contract scorecard (Round 3 §17)

Abbreviated; see `knowledge/` for full YAML. Status reflects **Round 3 narrative** — verify before treating as current gate.

| Invariant | KB pointer | Round 3 cited status |
|-----------|------------|----------------------|
| One-sentence primary design axis | `subnet.invariants.yaml` | Current objective pinned in `docs/objective-decision.md`; judge layer bounded separately |
| Validator-only development | `subnet.invariants.yaml#architecture.validator_only_development` | Still violated (reference miner + PROVER_SYSTEM) |
| Single-file validator pattern | `validator.contract.yaml` | Still violated by package layout; root `validator.py` stub removed |
| Push compute to miners | `subnet.invariants.yaml#compute_distribution` | Still violated |
| EMA for stability | `validator.rules.yaml` | Honored |
| Credibility tracking tuning | `incentive.primitives.yaml` | Wired; default exponent divergence documented in `docs/credibility-exponent-decision.md` |
| Secret eval sets | `validator.rules.yaml` | Still gated; not in judge pin |
| N miners profitability | `sybil.realities.yaml` | Still violated |
| Coldkey dedup ≠ sybil resistance | `sybil.realities.yaml` | Still violated by design |
| Validators not individually trusted | `trust.assumptions.yaml` | Softer-trust model documented for Chutes + voluntary HTTP peer checks |
| Synapse deprecated | `subnet.invariants.yaml` | Still violated |
| Open-source / corpus | `subnet.invariants.yaml` | Partially mitigated (`reasoning_only` export) |
| Hardware attestation | `trust.assumptions.yaml` | Miner verify attest documented as non-TEE hotkey signature over local Lean claim |
| Container / red-blue patterns | `container_execution.yaml`, `adversarial_red_blue.yaml` | Not adopted |
| Commit-reveal when needed | `subnet.invariants.yaml#commit_reveal` | Optional same-round binding documented; not chain-anchored fairness |
| Similarity detection | `validator.rules.yaml` | Byte-equal dedup evaded |
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

**Maintainers:** bump §17 when you materially change scope or close a whole section.
