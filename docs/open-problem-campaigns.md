# Open Problem Campaigns

This is a long-term direction for Lemma, not a launch requirement.

The current cadence stays simple: public generated theorem statements, easy /
medium / hard / extreme splits, fixed cadence, Lean verification, and
evidence-driven reward changes. Open-problem campaigns are a later lane for
slower, higher-stakes work: formalizing major mathematical targets, building
their dependency graphs, and rewarding verified progress toward them.

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
targets therefore need stronger statement governance than generated cadence
tasks.

## Statement Faithfulness

Statement faithfulness review is the plain question: did the Lean theorem say
the same thing as the informal theorem people care about?

Lean can check that a submitted proof proves an exact formal declaration. Lean
does not, by itself, check that the declaration is the real Riemann Hypothesis,
the real P vs NP problem, or the real graph-coloring conjecture. A fake win can
come from a statement that has the right name but the wrong definitions,
quantifiers, domains, constants, or assumptions.

Campaign review should therefore compare the formal statement with the original
source before the target is funded. Reviewers should check:

- the source problem and citation are explicit;
- the Lean definitions are standard, or any local definitions are justified;
- quantifiers, domains, constants, side conditions, and edge cases match the
  informal target;
- no local theorem, axiom, notation, or definition bakes in the desired result;
- the statement still means something important after all imports and
  dependencies are expanded.

For steady generated and curated cadence tasks, the game is narrower: prove the
published Lean statement. Those tasks have known witness proofs and are useful
for miner training, benchmarking, and routine reward traffic. For open-problem
campaigns, the network is making a stronger claim about mathematical progress,
so the statement itself needs review before any proof bounty matters.

## Faithfulness Review Protocol

Open-problem campaigns should treat statement review as a separate milestone
from proof search. A Lean proof can verify the wrong formal target perfectly, so
the campaign target is not official until the review record is complete.

Minimum review record:

- original informal source, citation, and license/attribution notes;
- upstream Lean source, commit, file, declaration, imports, and local
  definitions;
- plain-English restatement of what the Lean declaration asserts;
- comparison of quantifiers, domains, constants, hypotheses, edge cases, and
  intended definitions;
- dependency audit for local axioms, theorem aliases, notation, or definitions
  that could trivialize the target;
- reviewer names or handles, expertise note, date, and sign-off status;
- unresolved caveats, known mismatches, or reasons the statement is only a
  proxy for the informal problem.

Reward implication:

- `formalization_bounty` can pay for creating candidate Lean statements.
- `faithfulness_review_bounty` can pay reviewers for accepting, rejecting, or
  amending a candidate statement.
- `dependency_lemma_bounty` can start after a statement is at least reviewed.
- `final_theorem_bounty` should start only after the target is locked with a
  reviewed statement hash.

This is the main remaining human-review boundary for famous open problems.
Lemma can make the proof check reproducible, but it still needs human
mathematical judgment to say "this formal declaration is the thing we meant."

## Formal Conjectures Candidate Flow

[Formal Conjectures](https://google-deepmind.github.io/formal-conjectures/) is a
good candidate pool for future off-cadence work: it collects Lean 4 statements
of open conjectures, using Mathlib, from sources such as Erdős problem lists,
Wikipedia, MathOverflow, OEIS, papers, and Millennium-style problem lists. It is
not automatic canon for Lemma.

The campaign flow should be:

1. Select a candidate Lean statement from Formal Conjectures or another serious
   source.
2. Pin the upstream repository, commit, file, and declaration name.
3. Record the original informal source and any source-specific license or
   attribution requirements.
4. Compare the Lean declaration, imports, local definitions, and dependencies
   against the informal source.
5. Write a short faithfulness note explaining what the statement means and what
   was checked.
6. Lock the reviewed statement hash and deadline in the campaign registry.
7. Accept submit-when-ready Lean proofs against exactly that locked target.

The official target should be "Lemma reviewed and pinned this exact Lean
declaration at this exact commit." It should not be "prove any theorem with the
right famous name" or "Google posted this, so it must be the final canonical
statement."

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
  upstream_repo: google-deepmind/formal-conjectures
  upstream_commit: "<sha>"
  upstream_file: FormalConjectures/...
  upstream_declaration: "..."
statement_status: draft
faithfulness_status: unreviewed
faithfulness_review:
  source_citation: "<informal source>"
  reviewed_statement_hash: "<sha>"
  reviewers:
    - name: "<reviewer>"
      status: signed
  caveats: []
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
| `generated` | Steady traffic: easy / medium / hard / extreme recurring theorems, high throughput, predictable verify costs. |
| `curated` | benchmark or mathlib-adjacent theorem sets with explicit release governance. |
| `campaign` | long-horizon open-problem infrastructure and prerequisite lemmas. |
| `bounty` | submit-when-ready targets with explicit deadlines, rollover, and payout rules. |

The `campaign` and `bounty` lanes should not rely on validator-held secrets.
They should use public statements, public deadlines, reproducible verification,
and funded escrow when any live reward is offered.

## Candidate Source Pools

Useful future sources should be treated as inputs for review, not copied directly
into scored theorem campaigns.

| Source type | Why it is useful | Caution |
| --- | --- | --- |
| [Formal Conjectures](https://google-deepmind.github.io/formal-conjectures/) | Lean 4 statements of open conjectures, already shaped for automated theorem proving and Mathlib gap analysis. | Many statements still need faithfulness review, dependency triage, and difficulty labeling before rewards. |
| [Compfiles](https://dwrensha.github.io/compfiles/) / olympiad-style repositories | Good bridge between generated cadence theorems and harder curated work; many statements already have Lean context. | Solved entries are training/evaluation material, not bounty targets unless proofs are hidden or reformulated. |
| [PutnamBench](https://trishullab.github.io/PutnamBench/) | Hard undergraduate competition formalizations with a public benchmark and leaderboard culture. | Benchmark use must avoid training leakage and respect the dataset's intended evaluation split. |
| FirstProof-style research challenges | Close to the long-term "submit when ready" vision: unpublished or newly released research lemmas, expert grading, and high difficulty. | Usually starts as informal LaTeX, not a Lean theorem; Lemma would need a separate formalization and faithfulness-review phase before proof rewards. |

The safest bootstrap path is: import candidate ideas, create reviewed Lean
statements in a separate open-problem repo, publish the hash and deadline, then
accept submit-when-ready Lean proofs against that locked statement.

## Reward Shape

Campaign rewards should separate trail-building from the final proof. The final
theorem bounty can be winner-take-all or first-valid-proof-wins after the
statement is locked, but most campaign value comes before the final proof.
Bounties can reward:

1. informal-to-formal statement work;
2. faithfulness review;
3. definition infrastructure;
4. equivalence proofs;
5. dependency lemmas;
6. mathlib contributions;
7. final theorem proofs;
8. high-quality exposition.

Reward modes:

| Reward | Purpose |
| --- | --- |
| `formalization_bounty` | Turn an informal target into a Lean declaration and supporting definitions. |
| `faithfulness_review_bounty` | Review whether a candidate statement actually matches the informal target. |
| `dependency_lemma_bounty` | Prove prerequisite lemmas or Mathlib gaps needed by the campaign. |
| `infrastructure_bounty` | Build reusable definitions, imports, tests, or documentation for the target area. |
| `final_theorem_bounty` | Reward the first accepted proof of the locked reviewed target. |

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

The core subnet repo should not absorb a large open-problem library during the
current launch-focused stage. A later `LemmaOpenProblems`-style repo can own
campaign Lean files, registries, faithfulness docs, and roadmaps. The core
`lemma` repo should only add protocol support once the lane is ready: statement
hashing, submission format, payout rules, and verification hooks.

This keeps the launch repo focused on consensus-critical behavior while leaving
room for the long-term vision: a market for verified mathematical progress.
