# Open Problem Campaigns

This is a long-term direction for Lemma, not a v0 launch requirement.

The v0 lane stays simple: public generated theorem statements, easy / medium /
hard / extreme splits, fixed cadence, Lean verification, and evidence-driven
reward changes. Open-problem campaigns are a later lane for slower, higher-stakes work:
formalizing major mathematical targets, building their dependency graphs, and
rewarding verified progress toward them.

## Core Idea

Lemma should not start by asking miners to magically solve P vs NP, the Riemann
Hypothesis, or Navier-Stokes. The useful first step is to formalize those
mountains faithfully, then reward the trail-building:

1. informal open problem;
2. reviewed Lean statement;
3. faithfulness document;
4. dependency graph;
5. subproblem and lemma bounties;
6. verified Lean proof;
7. human mathematical review for major claims.

Lean acceptance is necessary, but for famous open problems it is not sufficient.
A malformed statement can be Lean-valid and mathematically worthless. Campaign
targets therefore need stronger statement governance than generated v0 tasks.

## Campaign Registry

A future campaign lane should use a public registry rather than ad hoc theorem
selection. Each entry should name the target, source authority, Lean declaration,
review status, dependency graph, and reward mode.

Example fields:

```yaml
id: clay.p_vs_np
title: "P vs NP"
status: open
domain: computational_complexity
source_authority:
  - clay_official
  - standard_textbook_reference
lean_statement:
  repo: LemmaOpenProblems
  file: Clay/PvsNP.lean
  declaration: Clay.PvsNP.P_ne_NP
statement_status: draft
faithfulness_status: unreviewed
mathlib_readiness: partial
dependencies:
  - complexity.languages
  - complexity.polynomial_time
  - complexity.verifiers
reward_mode:
  - formalization_bounty
  - lemma_bounty
  - final_theorem_bounty
```

Useful status fields are `draft`, `reviewed`, `canonical`, and `deprecated` for
statements; `unreviewed`, `reviewed`, and `expert-signed` for faithfulness.

## Source Lanes

Campaigns should be separate from the generated cadence lane.

| Lane | Role |
| --- | --- |
| `generated` | v0 traffic: easy / medium / hard / extreme recurring theorems, high throughput, predictable verify costs. |
| `curated` | benchmark or mathlib-adjacent theorem sets with explicit release governance. |
| `campaign` | long-horizon open-problem infrastructure and prerequisite lemmas. |
| `bounty` | submit-when-ready targets with explicit deadlines, rollover, and payout rules. |

The `campaign` and `bounty` lanes should not rely on validator-held secrets.
They should use public statements, public deadlines, reproducible verification,
and clear reward policy.

## Candidate Source Pools

Useful v1 sources should be treated as inputs for review, not copied directly
into scored theorem campaigns.

| Source type | Why it is useful | Caution |
| --- | --- | --- |
| [Formal Conjectures](https://google-deepmind.github.io/formal-conjectures/) | Lean 4 statements of open conjectures, already shaped for automated theorem proving and Mathlib gap analysis. | Many statements still need faithfulness review, dependency triage, and difficulty labeling before rewards. |
| [Compfiles](https://dwrensha.github.io/compfiles/) / olympiad-style repositories | Good bridge between v0 generated theorems and harder curated work; many statements already have Lean context. | Solved entries are training/evaluation material, not bounty targets unless proofs are hidden or reformulated. |
| [PutnamBench](https://trishullab.github.io/PutnamBench/) | Hard undergraduate competition formalizations with a public benchmark and leaderboard culture. | Benchmark use must avoid training leakage and respect the dataset's intended evaluation split. |
| FirstProof-style research challenges | Close to the long-term "submit when ready" vision: unpublished or newly released research lemmas, expert grading, and high difficulty. | Usually starts as informal LaTeX, not a Lean theorem; Lemma would need a separate formalization and faithfulness-review phase before proof rewards. |

The safest bootstrap path is: import candidate ideas, create reviewed Lean
statements in a separate open-problem repo, publish the hash and deadline, then
accept submit-when-ready Lean proofs against that locked statement.

## Reward Shape

The final theorem bounty can be first-valid-proof-wins, but most campaign value
comes before the final proof. Bounties can reward:

1. informal-to-formal statement work;
2. faithfulness review;
3. definition infrastructure;
4. equivalence proofs;
5. dependency lemmas;
6. mathlib contributions;
7. final theorem proofs;
8. high-quality exposition.

For P vs NP, the early campaign should be "build the complexity-theory stack,"
not "prove P != NP tomorrow." Good early subgoals include languages, encodings,
polynomial-time decision, polynomial-time verification, reductions, SAT, and
NP-completeness infrastructure.

## Anti-Fake-Win Requirements

Campaign claims need stricter checks than ordinary generated tasks:

- locked theorem statement and source hash;
- no `sorry`, unapproved `axiom`, or unsafe imports;
- no local weakening or shadowing of canonical definitions;
- independent rebuild on pinned toolchain / Mathlib;
- dependency audit for major claims;
- human expert review of faithfulness and significance;
- public reproducibility package for large wins.

This is especially important for famous open problems, where the risk is not
only "no one solves it," but "someone proves a statement that was never the real
problem."

## Repository Boundary

The core subnet repo should not absorb a large open-problem library during v0.
A later `LemmaOpenProblems`-style repo can own campaign Lean files, registries,
faithfulness docs, and roadmaps. The core `lemma` repo should only add protocol
support once the lane is ready: statement hashing, submission format, payout
rules, and verification hooks.

This keeps the launch repo focused on consensus-critical behavior while leaving
room for the long-term vision: a market for verified mathematical progress.
