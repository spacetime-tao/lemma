# Open Problem Campaigns

This is a long-term direction. It is not required for v0 launch.

The v0 lane stays simple:

- public generated theorem statements;
- easy, medium, and hard splits;
- fixed cadence;
- Lean verification;
- evidence-driven reward changes.

Open-problem campaigns would be a slower, higher-stakes lane for major math
targets and the work needed to formalize them.

## Core Idea

Do not start by asking miners to solve P vs NP or the Riemann Hypothesis.

Start by building the formal trail:

1. informal problem;
2. reviewed Lean statement;
3. faithfulness note;
4. dependency graph;
5. subproblem bounties;
6. verified Lean proof;
7. human review for major claims.

Lean acceptance is necessary, but not enough for famous problems. A bad Lean
statement can be valid Lean and still not mean the real problem.

## Campaign Registry

A future campaign lane should use a public registry.

Each entry should name:

- target;
- source authority;
- Lean declaration;
- review status;
- dependency graph;
- reward mode.

Example:

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

## Source Lanes

| Lane | Role |
| --- | --- |
| `generated` | v0 traffic with predictable verify cost. |
| `curated` | Reviewed benchmark or Mathlib-adjacent theorem sets. |
| `campaign` | Long-horizon open-problem infrastructure. |
| `bounty` | Submit-when-ready targets with deadlines and clear payout rules. |

Campaign and bounty lanes should use public statements, public deadlines,
reproducible verification, and clear rewards.

Do not rely on validator-held secrets.

## Candidate Sources

Treat sources as inputs for review, not as ready-to-score tasks.

| Source | Useful because | Caution |
| --- | --- | --- |
| [Formal Conjectures](https://google-deepmind.github.io/formal-conjectures/) | Lean 4 statements shaped for ATP and Mathlib gap work. | Needs faithfulness review and difficulty labels. |
| [Compfiles](https://dwrensha.github.io/compfiles/) | Bridge from generated tasks to harder curated work. | Solved entries can leak training answers. |
| [PutnamBench](https://trishullab.github.io/PutnamBench/) | Hard formalized competition problems. | Respect eval splits and avoid leakage. |
| FirstProof-style challenges | Close to submit-when-ready research work. | Usually starts as informal LaTeX and needs formalization first. |

Safe bootstrap path:

1. Import candidate ideas.
2. Create reviewed Lean statements in a separate repo.
3. Publish statement hash and deadline.
4. Accept Lean proofs against the locked statement.

## Reward Shape

The final theorem bounty can be first-valid-proof-wins.

Most value may come earlier:

- statement formalization;
- faithfulness review;
- definitions;
- equivalence proofs;
- dependency lemmas;
- Mathlib contributions;
- final theorem proofs;
- clear exposition.

For P vs NP, the early campaign should be "build the complexity-theory stack,"
not "prove P != NP tomorrow."

## Anti-Fake-Win Rules

Campaign claims need strict checks:

- locked theorem statement and source hash;
- no `sorry`;
- no unapproved `axiom`;
- no unsafe imports;
- no weaker local definitions;
- independent rebuild on the pinned toolchain;
- dependency audit for major claims;
- human expert review;
- public reproducibility package for large wins.

The main risk is proving a statement that was never the real problem.

## Repo Boundary

The core `lemma` repo should not absorb a large open-problem library during v0.

A later `LemmaOpenProblems` repo can own Lean files, registries, faithfulness
docs, and roadmaps.

The core repo should add protocol support only when the lane is ready.
