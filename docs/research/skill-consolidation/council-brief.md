# Council brief — skill consolidation

You are one member of a council. Several models are solving this task independently
and blind to each other; a judge will consolidate the reports afterward. Solve it
yourself, completely. Do not speculate about what other members might say.

Work read-only. **Do not edit, create, or delete any file.** Your final message is
the entire deliverable.

## Repo

`/data/codes/coding-ritual` — a meta-repo that curates third-party agent-harness
repos (tracked read-only as git submodules under `reference_harnesses/`) and
distills the best patterns into a reusable harness.

## The task

63 agent "skills", harvested from three well-regarded harness repos, have already
been sorted into 14 routing buckets. **Many of them solve the same problem two or
three times. Find the duplicates and remove them.**

For each bucket, reduce it to the **smallest set of skills that preserves every
distinct advantage**.

The test for every removal is: **what does this skill do that nothing else kept in
this bucket does?** If the answer is "nothing", it goes. If there is a real answer,
it survives — either as its own skill, or as merged content inside another skill,
in which case the merge must demonstrably carry that capability.

**There is no target count, and no minimum.** A bucket collapses to one skill if one
skill genuinely covers it; it returns all five of its inputs if it holds five
distinct jobs. The number is an outcome of your analysis, never an input to it.

Two failure modes, and the second is worse:

1. Keeping near-duplicates because their wording differs. This is what the exercise
   exists to catch.
2. Crushing distinct capabilities together because a smaller number looks tidier.
   A merge that destroys an advantage is worse than keeping two skills.

## Input

`docs/research/skill-consolidation/roster-in.csv` — the 63 skills. Columns:
`primary_bucket_id`, `primary_bucket`, `name`, `harness`, `capability_family`,
`family_relation`, `repo_path`, `line_count`, `description`. Every `repo_path` is
verified readable from the repo root.

Two pre-computed hints, both **hypotheses to test, not conclusions to inherit**:

- `capability_family` groups skills believed to address the same underlying
  capability.
- `family_relation` says how those members relate — `substitutes` (adopt one, not
  both), `complements` (two halves of one protocol), `pipeline` (sequential stages),
  `genus` (same area, different scope, not interchangeable), `singleton`.

Overturn either where the files disagree with them. Duplication may also cross
family lines — test pairwise across the whole bucket, not only within families.

Supporting context, useful but not authoritative:
`docs/plans/skill-consolidation-plan.md` (the plan this runs under),
`harness_lifecycle/inventory/skill-buckets.md` (how the buckets were derived).

## Method requirement

**Read the full `SKILL.md` and its bundled assets for every skill you rule on.
Never decide from the one-line description.** Descriptions in this corpus have
already misled two prior reviewers:

- `teach` reads like a documentation skill; it is a multi-session spaced-repetition
  pedagogy system whose own examples are yoga and theoretical physics.
- `subagent-driven-development` reads like an orchestration skill; superpowers' own
  `writing-plans` and `executing-plans` declare it the *recommended plan executor*,
  interchangeable with `executing-plans`.

When you rule on a skill, cite the file content you relied on.

## What to record per skill

Job · trigger (does the description state real firing conditions, or just summarize
the workflow?) · mechanism (gates, checklists, subagent dispatch, templates) ·
enforcement strength (hard stop conditions vs prose advice that can be ignored
without noticing) · dependencies (external tools, MCP servers, trackers, language
assumptions) · context cost (line count, assets, progressive disclosure) ·
portability (repo/org/language-specific assumptions) · **couplings** — other skills
it names as required sub-skills. Couplings matter: selecting a winner that depends
on skills you dropped is a defect, so check it.

When two overlapping skills must be ranked, rank on: coverage of the job,
enforcement strength, trigger quality, portability, context cost, dependency cost.
Ties break toward the more portable and cheaper skill, not the more elaborate one.

## Three degenerate buckets

After the exclusion of ten skills (mattpocock's `misc/` and `in-progress/` folders,
which his own `CLAUDE.md` defines as low-confidence promotion tiers), three buckets
have little or nothing left to consolidate:

- **Bucket 12** — one skill (`setup-matt-pocock-skills`).
- **Bucket 13** — two skills in different families.
- **Bucket 14** — two skills (`teach`, `wait-what`), already flagged out of scope
  for adoption since their output is consumed by people, not by the software system.

Handle them briefly and say what you would do. Do not pad them.

## Deliverable

A self-contained report. Use this structure:

### Part 1 — Per bucket (all 14)

For each bucket, in order:

- **Kept** — each skill with the one-sentence answer to the removal test: what it
  does that nothing else kept in this bucket does.
- **Dropped** — each skill with the reason, and which kept skill (if any) absorbs
  its capability.
- **Merges** — for each proposed merge: what each side does, what is unique to each,
  what the merged skill contains, what the merge costs (content dropped, conflicts
  resolved and which side won, resulting size), and whether the result is still one
  coherent skill or a bag of two wearing one name.
- **Verdict line** — `N in → M out`.

### Part 2 — Cross-bucket check

Buckets analysed in isolation miss things. Report: any kept skill whose required
sub-skills you dropped in another bucket; any skill you kept in one bucket and
dropped in another; any two kept skills in different buckets that actually overlap.

### Part 3 — Capability-loss ledger

Every capability that does not survive into a kept skill: source skill, what is
lost, why it was acceptable to lose, and whether it is recoverable later.

### Part 4 — Final roster

The complete final list of skills with their buckets, and the total: 63 in → N out.

### Part 5 — Confidence and open questions

Where you are least sure, which calls you would revisit first, and what evidence
would change your mind. State which way you lean rather than hedging.

## Rules

- Be decisive. State positions, not option surveys.
- Cite file content for every non-obvious ruling.
- Report honestly: if you could not read something or ran out of room to analyse a
  bucket properly, say so explicitly rather than covering the gap with plausible
  prose. An acknowledged gap is useful; a fabricated ruling is not.
