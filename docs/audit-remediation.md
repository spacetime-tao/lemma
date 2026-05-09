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

1. Delete or replace **`proof_intrinsic_score`** (elaborator-backed metric vs length heuristic).
2. Raise **`LEMMA_REPUTATION_CREDIBILITY_EXPONENT`** default toward **2.5** (align with documented spec) — one-line default change + rationale.
3. **Expand `judge_profile_sha256`** (or sibling hash) to cover subnet-critical knobs currently outside the pin (~18 fields in Round 3).
4. **Fail closed** when `computed_body_hash` missing — remove fail-open in `synapse_miner_response_integrity_ok`; update/remove tests that codify bypass.
5. **Per-validator salt** in attest spot-verify selection hash (reduces predictable skip + UID grinding).
6. **Sybil / Pareto:** move beyond coldkey dedup toward mechanism aligned with Affine-style winners-take-all-per-subset (needs design).
7. Drop **`LEMMA_PROBLEM_SOURCE=frozen`** / bundled JSON if policy allows (large policy decision).
8. **Aggressively cut CLI / wizard / `main.py` surface** (Part 2 scale stats).
9. Move **`lemma/catalog/`** dev tooling to `tools/` (audit flagged twice).
10. **Plan structural redesign** — container-based miner artifact + kernel-only scoring (see §12); drops judge stack.

---

## 3. Integrity, transport, and “fail open” behavior

| ID | Issue | Source § | Priority | Remediation direction | Key refs (verify in tree) |
|----|--------|----------|----------|------------------------|---------------------------|
| **I1** | `synapse_miner_response_integrity_ok` returns **True** when `computed_body_hash` is missing → middleboxes can strip headers; combined with attest/trace concerns | R3 §3.1, §6 | P1 | Policy: **fail closed** for production profiles when header absent; or staged rollout with metric | `lemma/protocol.py` (`synapse_miner_response_integrity_ok`) |
| **I2** | `deadline_block is None` may bypass deadline path if fields stripped | R3 §6 | P1 | Tie deadline rejection to same integrity gate; reject `None` when challenge required it | `lemma/validator/epoch.py`, `protocol.py` |
| **I3** | Single `block_after_query` for batch — timing games | R3 §6 | P2 | Per-response block or documented acceptance | `epoch.py` |
| **I4** | Synapse transport deprecated in KB vs Epistula | R3 §5.15, §11 | P4 | Track `knowledge/` transport migration; out of scope for “quick fix” | `protocol.py`, `knowledge/` |

**2026-05 progress:** I1/I2 patched in `synapse_miner_response_integrity_ok`: validator responses now fail closed when `computed_body_hash` is missing, mismatched, or when `deadline_block` is missing from the miner response.

---

## 4. Scoring objective — “measures the wrong thing”

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **O1** | Rank mixes kernel-verifiable proof with **LLM judge** on miner prose; lowering proof weight to default `w=0.10` reduces text-heuristic padding risk but leaves judge dominance explicit | R3 §2, §11 | P4 / product | Explicit product decision: cap judge, judge-free mode, red/blue, or container-only scoring |
| **O2** | `primary_design_axis` / one-sentence rule in KB violated by current honest description | R3 §2.3 | P4 | Rewrite mechanism doc or change mechanism to match KB |
| **O3** | Pareto + coldkey dedup + identical dedup still allow sybil farming per R3 math | R3 §2.2, §8, §12 | P2/P4 | Economic modeling; not fixable by parser alone |

---

## 5. `proof_intrinsic` — residual gaming

**Decision note:** [proof-intrinsic-decision.md](proof-intrinsic-decision.md) records the current stance: keep the heuristic only as a low-weight bootstrap signal, do not raise its default weight, and do not add more regex padding detectors as the main fix. Default `LEMMA_SCORE_PROOF_WEIGHT` is now `0.10`.

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **P1** | Comment stripping defeats **one** padding class; **string literals**, trivial `have … by trivial`, long names still inflate | R3 §2.1 | P2 | Default weight lowered; next real fix is Lean/elaborator-backed metrics, not more text-shape patches | `lemma/scoring/proof_intrinsic.py`, `config.py`, `docs/proof-intrinsic-decision.md` |
| **P2** | Default credibility exponent `1.0` vs KB mention of `2.5` | R3 §7 | P3 | Align default or document divergence | `config.py`, `scoring/reputation.py` |
| **P3** | Credibility rises on Lean pass; padding that passes Lean **does not** get penalized by cred | R3 §7 | P2 | Accept or add orthogonal signal |
| **P4** | Spot-verify skip returns pass → cred EMA increases without verify | R3 §3.2, §7 | P1 | Do not treat attest-only path as verify success for cred; split signals | `epoch.py`, `protocol_attest.py` |

---

## 6. Miner verify attestation (`protocol_attest`)

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **A1** | Attest preimage does not bind **reasoning** (judge axis); trace swap vs body_hash story | R3 §3.1 | P2 | Document threat model; optional bind extension |
| **A2** | No validator hotkey in attest; cross-validator replay | R3 §3.1 | P2 | Add bind field + version byte if product wants it |
| **A3** | Spot fraction `<1` → predictable selection; no per-validator salt; UID grinding | R3 §3.2 | P1 | Salted selection, raise minimum spot, or separate cred impact |
| **A4** | On spot skip, theorem/proof mismatch not caught by verify | R3 §3.3 | P1 | Always validate theorem id vs response before scoring; cheap checks |
| **A5** | “TEE” naming vs actual user-space Docker attest | R3 §3.4 | P3 | Docs + naming; no fake hardware claims |

**2026-05 progress:** P4/A3 credibility impact patched: attest-trusted spot skips remain scoreable, but no longer improve verify credibility. Credibility only increases from validator Lean verification; full-verify failures still lower it. Spot selection now accepts `LEMMA_MINER_VERIFY_ATTEST_SPOT_VERIFY_SALT`; `judge_profile_sha256` pins its SHA-256 without exposing the salt.

---

## 7. Commit–reveal

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **C1** | Two phases **same validator process**, no chain delay — may not match threat model that CR usually assumes | R3 §4 | P4 | Document “why CR exists”; consider removal if no wire threat |
| **C2** | Miner `forward.py` cache **no eviction** — memory growth | R3 §4.1 | P1 | TTL / max entries / keyed by validator id |
| **C3** | Cache key `(theorem_id, metronome_id)` → cross-validator overwrite | R3 §4.2 | P1 | Include validator identity or disable CR for multi-validator until fixed |
| **C4** | `looks_like_commitment_hex` vs `0x` — regex strict; reveal path strips `0x` | R3 §4.3 | P2 | Accept `0x` consistently everywhere | `protocol_commit_reveal.py`, `epoch.py`, miner forward |
| **C5** | `json.dumps(..., sort_keys=True)` on **list** in `reasoning_blob_for_commit` — meaningless flag | R3 §4.4 | P3 | Remove dead arg or serialize deterministically as designed |

**2026-05 progress:** C2/C3/C4/C5 patched for the usable commit-reveal path: miner commit cache is TTL/max-entry bounded, cache keys include validator dendrite hotkey, commitment hex accepts optional `0x`, and the no-op `sort_keys=True` was removed from list serialization.

---

## 8. Judge profile peer quorum

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **J1** | HTTP plaintext / no auth; MITM | R3 §5.1 | P2 | TLS, auth, or document “operator honor system only” |
| **J2** | All-of-N flaky; no Byzantine resistance | R3 §5.1 | P2 | k-of-n, retries, health checks |
| **J3** | Hash omits many subnet-critical env vars | R3 §5.3 | P2 | Expand profile hash or separate “scoring profile” attestation |
| **J4** | `LEMMA_JUDGE_PROFILE_ATTEST_SKIP` foot-gun | R3 §5.1 | P3 | Loud metrics / mainnet deny |

**2026-05 progress:** J3 patched by broadening `judge_profile_sha256` into a validator scoring profile: it now covers the judge stack plus deterministic problem cadence, verification timeout/image policy, scoring blend/dedup/reputation settings, and protocol hooks that affect response acceptance.

---

## 9. Judge JSON / prompt / FakeJudge

| ID | Issue | Source § | Priority | Remediation direction | Key refs |
|----|--------|----------|----------|------------------------|----------|
| **G1** | **Dedupe** of identical dicts across parse passes → **echo** rubric may collapse to one valid score | R3 §10.1 | P2 | Policy: e.g. reject if rubric text appears in miner fence; require single extraction path; tests for echo |
| **G2** | Two **distinct** valid rubrics in trace → parse fails → miner dropped | R3 §10.1 | P2 | UX: fail-soft rule or strip miner fences only |
| **G3** | Sanitizer only escapes ``` ; many other injection channels | R3 §10.2–10.3 | P2 | Expand sanitizer + model-side prompts; injection tests |
| **G4** | **FakeJudge** length curve; missing API key falls back with log only | R3 §10.4 | P1 | Fail closed in production profile; align `LEMMA_FAKE_JUDGE` parsing | `judge/fake.py`, `epoch.py`, `config.py` |

**2026-05 progress:** G4 patched in validator judge construction: live validator epochs now raise when judge API keys are missing or `LEMMA_FAKE_JUDGE` is forced; dry-run still uses FakeJudge by default.

---

## 10. Problem supply — templates, seed, frozen

| ID | Issue | Source § | Priority | Remediation direction |
|----|--------|----------|----------|------------------------|
| **R1** | 28 templates enumerable; SHA256 mix is **public** — offline cache still works | R3 §9, §9.1 | P2 | Accept or enlarge / rotate builders with governance |
| **R2** | `generated_registry_sha256` may not hash builder **bodies** — skew risk | R3 §9.3 | P0/P1 | Include body hash or codegen fingerprint |
| **R3** | `RNG_MIX_TAG` not in registry pin | R3 §9.3 | P1 | Version tag in registry |
| **R4** | Frozen miniF2F route / gate consistency | R3 §9.2 | P1 | Ensure `resolve_problem` respects gates uniformly | `problems/factory.py` |
| **R5** | Hardcoded toolchain / mathlib / sandbox `:latest` etc. | R3 §13 | P3 | Digest-pinned images in prod docs; fewer `:latest` |

**2026-05 progress:** R2/R3 patched in `generated_registry_canonical_dict`: the generated-registry fingerprint now includes `RNG_MIX_TAG`, builder count/split metadata, and a source hash for each builder function. `docs/generated-problems.md` now reflects the live 28-builder mix.

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
- **`_stats` / `_commit_reveal_cache`** globals in forward handler (unbounded cache overlaps §7 **C2**).
- Stub proof for `two_plus_two` in production path per audit.
- **`synapse_payload_error` triple invocation** in commit-reveal mode clarified: incoming challenge checks now skip response-only validation; outgoing commit/reveal responses still run response validation.

### 13.6 Configuration (`config.py`)

- File cited ~**980 LoC** — growth without removing scaffolding.
- **102 `Field` / 103 `AliasChoices`** — lower-case aliases allegedly unused in production.
- Triple aliases on several wallet/prover fields.
- **`allow_noncanonical_judge_model`** — zero readers per audit grep snapshot (verify before delete).
- Resolver collapse opportunities (`anthropic` vs OpenAI keys).
- **`validator_judge_stack_strict`** vs unreachable Anthropic judge branch on validator.
- Six env names for two wallet values.
- Reserved protocol toggles default **False** but many Fields persist.
- Timeout-split / prover self-rejection knobs — validator-side usefulness questioned in audit.

### 13.7 Tests (coverage imbalance)

- ~**20 %** mechanism math tests vs **~40 %** protocol vs **~42 %** glue vs **~7 %** pure CLI — author breakdown; periodically recompute.
- Tests called out as low value: `uv_bootstrap` (removed), `try_prover` flag tables (moved to `lemma-cli`), `problem_views` title case, `protocol_migration` no-op test (removed), **`test_protocol.py` codifying body-hash fail-open**, thin `prompt_sanitize` coverage.
- **Missing:** `tests/test_rewards.py` for **`entry_from_scores`** / rewards assembly (audit claim).

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
| One-sentence primary design axis | `subnet.invariants.yaml` | Still violated |
| Validator-only development | `subnet.invariants.yaml#architecture.validator_only_development` | Still violated (reference miner + PROVER_SYSTEM) |
| Single-file validator pattern | `validator.contract.yaml` | Still violated by package layout; root `validator.py` stub removed |
| Push compute to miners | `subnet.invariants.yaml#compute_distribution` | Still violated |
| EMA for stability | `validator.rules.yaml` | Honored |
| Credibility tracking tuning | `incentive.primitives.yaml` | Wired; default exponent cited as wrong vs spec |
| Secret eval sets | `validator.rules.yaml` | Still gated; not in judge pin |
| N miners profitability | `sybil.realities.yaml` | Still violated |
| Coldkey dedup ≠ sybil resistance | `sybil.realities.yaml` | Still violated by design |
| Validators not individually trusted | `trust.assumptions.yaml` | Softer-trust model (Chutes + voluntary HTTP quorum) |
| Synapse deprecated | `subnet.invariants.yaml` | Still violated |
| Open-source / corpus | `subnet.invariants.yaml` | Partially mitigated (`reasoning_only` export) |
| Hardware attestation | `trust.assumptions.yaml` | “TEE” = model name; not remote attestation |
| Container / red-blue patterns | `container_execution.yaml`, `adversarial_red_blue.yaml` | Not adopted |
| Commit-reveal when needed | `subnet.invariants.yaml#commit_reveal` | Cited as misapplied |
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
