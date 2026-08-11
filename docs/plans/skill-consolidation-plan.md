# Skill Consolidation — Plan

**Status:** drafted, awaiting approval. Not started.
**Input:** `harness_lifecycle/inventory/skill-buckets.csv` (73 skills, 14 buckets).
**Goal:** reduce each bucket to the **smallest set of skills that preserves every
distinct advantage** — with the reasoning, the merge analysis, and the capability
cost written down.

## Purpose

We have 73 skills across three reference harnesses, bucketed by routing intent.
Many solve the same problem three times. **The point of this exercise is finding
and removing duplicates.** Where several skills do one job, one wins and the rest
go. Where a losing skill carries something the winner lacks, that capability is
merged in rather than discarded.

There is **no target count**. A bucket collapses to one skill if one skill covers
it; it stays at four if it holds four genuinely distinct jobs. The number is an
outcome of the analysis, never an input to it. The failure modes on both sides are
equally real: padding a bucket with near-duplicates because they look different,
and crushing distinct capabilities together because a smaller number looks tidier.
The second is the one to guard hardest against — a merge that destroys an advantage
is worse than keeping two skills.

The test for every removal is: **what does this skill do that nothing else kept
does?** If the answer is "nothing", it goes. If there is an answer, it survives —
either as its own skill or as merged content in another, and the merge must
demonstrably carry it.

This plan covers **analysis and selection only**. Writing merged `SKILL.md` files
is a separate, later piece of work; nothing here edits the harness.

## Input set

**63 skills.** Ten mattpocock skills are excluded per instruction — everything
under `skills/misc/` and `skills/in-progress/`:

| Excluded | Folder | Bucket |
|---|---|---|
| `claude-handoff` | in-progress | 10 |
| `loop-me` | in-progress | 1 |
| `setup-ts-deep-modules` | in-progress | 12 |
| `writing-beats` | in-progress | 14 |
| `writing-fragments` | in-progress | 14 |
| `writing-shape` | in-progress | 14 |
| `git-guardrails-claude-code` | misc | 12 |
| `migrate-to-shoehorn` | misc | 4 |
| `scaffold-exercises` | misc | 14 |
| `setup-pre-commit` | misc | 12 |

The exclusion is defensible on its own terms: mattpocock's `CLAUDE.md` defines
these folders as promotion tiers — `in-progress/` is beta, `misc/` is "kept around
but rarely used" — so both are the author's own low-confidence shelf.

## Where the duplicates actually are

Buckets differ enormously in how much duplication they contain, and
`family_relation` already predicts it.

- A bucket dominated by a **`substitutes`** family is mostly duplication: three
  skills doing one job. These collapse hard and lose nothing — this is where the
  exercise pays.
- A bucket of **singleton** families contains little or no duplication. Every skill
  is a different job, and the honest result is that most of them survive.

Bucket 9 is the extreme: five skills, five singleton families, zero substitution.
`ci-cd-and-automation`, `deprecation-and-migration`, `observability-and-instrumentation`,
`shipping-and-launch` and `wizard` share a routing bucket and nothing else. If the
analysis returns five, that is the correct answer for that bucket, not a failure.

**Two failure modes, guarded separately.** Keeping near-duplicates because their
wording differs is the one the exercise exists to catch. Crushing distinct
capabilities together because a smaller number looks tidier is the more damaging
one, and the harder to detect after the fact. Every capability dropped or thinned
in a merge is logged in a capability-loss ledger, so a bad compression is visible
as a cost rather than hidden inside a clean-looking roster.

## Scoping

Expected duplication is driven by family structure, not skill count. The last
column is a **prior to be tested, not a quota** — the files decide.

| # | Bucket | Skills | Families | Shape | Expected duplication |
|---|---|---:|---:|---|---|
| 1 | Discovery, Requirements & Decisions | 9 | 4 | 1 genus(3) + 2 substitutes(3,2) + 1 singleton | **high** — largest bucket, two substitute clusters |
| 2 | Planning & Work Management | 5 | 3 | 1 genus(3) + 2 singletons | moderate |
| 3 | Architecture & Modeling | 5 | 4 | 1 genus(2) + 3 singletons | low — mostly distinct jobs |
| 4 | Implementation & Refactoring | 8 | 6 | 1 substitutes(3) + 5 singletons | moderate — one clear cluster, 5 distinct jobs |
| 5 | Testing & Runtime Validation | 4 | 2 | 1 substitutes(3) + 1 singleton | **high** |
| 6 | Debugging & Optimization | 4 | 2 | 1 substitutes(3) + 1 singleton | **high** |
| 7 | Review & Completion Assurance | 6 | 4 | 1 substitutes(2) + 1 complements(2) + 2 singletons | moderate |
| 8 | Version Control & Change Integration | 4 | 3 | 1 genus(2) + 2 singletons | low |
| 9 | Release, Migration & Operations | 5 | 5 | 5 singletons | **none expected** — no substitution at all |
| 10 | Orchestration, Handoff & Context Continuity | 3 | 3 | 3 singletons | **none expected** |
| 11 | Harness Routing & Agent-System Authoring | 5 | 2 | 2 substitutes(3,2) | **highest** — every member is in a substitute cluster |
| 12 | Repository Tooling & Guardrails | 1 | 1 | singleton | **degenerate** |
| 13 | Engineering Research & Durable Documentation | 2 | 2 | 2 singletons | **degenerate** |
| 14 | Human Learning, Content & Conversation | 2 | 2 | 2 singletons | **degenerate** |

The yield is concentrated in buckets 11, 5, 6, and 1. Buckets 9 and 10 will
probably return everything they were given, and that is a result, not a miss.
Three buckets have nothing left to consolidate — see *Open decisions*.

## Decision procedure

Applied per bucket, in order.

### Step 1 — Build a capability profile per skill

Read the **full `SKILL.md` and its assets**, not the one-line description. This is
non-negotiable: descriptions in this corpus have already proven misleading twice —
`teach` reads like a docs skill and is a spaced-repetition pedagogy system;
`subagent-driven-development` reads like an orchestration skill and is superpowers'
recommended plan executor. Record for each skill:

- **Job** — the one sentence of what it actually does.
- **Trigger** — when it fires, and whether the description states real triggering
  conditions or just summarises the workflow.
- **Mechanism** — checklists, gates, subagent dispatch, templates, questions.
- **Enforcement** — hard gates and stop conditions vs prose advice. A skill that
  can be ignored without noticing is weaker than one that blocks.
- **Dependencies** — external tools, MCP servers, trackers, language assumptions.
- **Cost** — line count, asset count, whether it uses progressive disclosure.
- **Portability** — repo/org/language-specific assumptions that would not survive
  adoption elsewhere.
- **Couplings** — other skills it names as required sub-skills. These create
  adoption chains and must be recorded; picking a winner that depends on three
  skills we dropped is a defect.

### Step 2 — Resolve within each family

`family_relation` in the CSV already says how members relate; use it as the
starting hypothesis and overturn it if the files disagree.

- **`substitutes`** → pick exactly one winner. This is where consolidation is
  genuinely free.
- **`complements`** → the members are one unit (`requesting-code-review` +
  `receiving-code-review` are two halves of one protocol). Treat as a single
  candidate; do not split them to hit a count.
- **`pipeline`** → sequential stages of one workflow; same treatment. *(No pipeline
  families survive the exclusion — all three prose skills were excluded.)*
- **`genus`** → same area, different scope. Decide explicitly whether the broad
  one absorbs the narrow one, or both must survive.
- **singleton** → nothing to resolve; carry to step 3 as its own candidate.

### Step 3 — Test every surviving candidate for redundancy

Run the removal test pairwise across the bucket, ignoring family lines — families
are the starting hypothesis, not the boundary. For each candidate: **what does it
do that nothing else kept does?** No answer means it goes.

When two candidates do overlap, rank them on:

1. **Coverage** of the job — full vs a slice.
2. **Enforcement strength** — does it actually change behaviour, or is it advice
   that can be ignored without noticing.
3. **Trigger quality** — a skill that never fires is worth nothing.
4. **Portability** — fewest repo/language/tracker assumptions.
5. **Context cost** — always-on weight; progressive disclosure preferred.
6. **Dependency cost** — external tools, MCP, credentials.

Ties break toward the more portable and cheaper skill, not the more elaborate one.

The output is the smallest set where every member survives the removal test.
Whether that is one skill or five is the bucket's answer.

### Step 4 — Merge analysis (whenever a bucket keeps more than one)

For every kept skill, and for each pair that came close to collapsing:

- **What each does** — the capability profiles side by side.
- **What is unique to each** — the specific answer to the removal test, i.e. the
  reason it survived.
- **What a merge would produce** — the combined skill's job, triggers, structure.
- **What a merge would cost** — content dropped, conflicts resolved (and which
  side won), estimated size, and whether the result is still one coherent skill
  or a bag of two wearing one name.
- **Verdict** — merge, or keep separate with the reason stated.

A pair that does not fuse into something coherent stays separate. That is a
result, not a failure to compress.

### Step 5 — Log the losses

Every capability from a non-selected skill that does not survive into a
representative goes in the ledger with: source skill, capability, why dropped,
and whether it is recoverable later. Silent loss is the failure mode this step
exists to prevent.

## Phases

Each phase ends with a check that can fail.

### Phase 0 — Freeze the input set

Emit `roster-in.csv` (the 63 in-scope skills) from `skill-buckets.csv` plus the
exclusion rule.
**Verify:** row count is exactly 63; the 10 excluded names are absent; every
bucket's membership matches the scoping table above.

### Phase 1 — Capability profiles

One pass per bucket. Full read of every member's `SKILL.md` and assets, producing
the step-1 profile.
**Verify:** every one of the 63 skills has a profile; every profile cites the file
it was read from; no profile is derived from the description alone.

### Phase 2 — Per-bucket consolidation

Apply steps 2–4. One document per bucket.
**Verify:** every kept skill has a stated answer to the removal test; every
dropped skill has a stated reason; every kept set has a completed merge analysis.
A bucket returning all its inputs is acceptable only with per-skill justification.

### Phase 3 — Cross-bucket reconciliation

Buckets are analysed independently, so this pass catches what that misses:

- A representative whose required sub-skills were dropped in another bucket.
- The same skill winning in one bucket and being dropped in another it appears in
  as a secondary.
- Two representatives in different buckets that turn out to overlap.

**Verify:** no representative has an unresolved dependency on a dropped skill.

### Phase 4 — Final roster

Emit `roster-out.csv` (the chosen skills, bucket, disposition, rationale) and a
summary listing the final skills, the merges, and the full capability-loss ledger.
**Verify:** every bucket accounted for; every input skill has a disposition
(`selected` / `merged-into:<x>` / `dropped:<reason>` / `excluded`); counts
reconcile against the 63.

## Outputs

```text
docs/research/skill-consolidation/
  roster-in.csv              63 in-scope skills (phase 0)
  bucket-NN-<slug>.md        one per bucket: profiles, decision, merge analysis
  capability-loss.md         the ledger
  roster-out.csv             final roster, machine-readable
  SUMMARY.md                 final skill list + merges + losses
```

`.claude/project/docs-index.md` gets one pointer row on completion.

## Execution mechanics

- **One worker per bucket**, fresh context, per `.claude/rules/core/01-delegation.md`.
  Each is given only its bucket's skill files, the decision procedure, and its
  output path — not this conversation's history.
- Buckets write to separate files, so workers can run in parallel safely.
- Phase 3 is coordinator work; it needs all buckets in view and cannot be delegated
  per-bucket.
- Beads: one epic plus a task per bucket, created at execution start.
- The degenerate buckets (12, 13, 14) get no worker — they are resolved inline.

## Open decisions

These change the work and are the user's call. Stated assumptions are what will
happen absent an instruction otherwise.

1. **Bucket 12 has one skill left.** `setup-matt-pocock-skills` configures
   *mattpocock's own* tracker, label vocabulary, and doc layout — a bootstrap for
   his suite, not a general capability. **Assumption:** report the bucket as having
   no viable representative rather than promote it by default.
2. **Bucket 14 is already marked out of scope for adoption** and now holds only
   `teach` and `wait-what` — a pedagogy workspace and a 7-line conversational
   macro, with nothing in common. **Assumption:** skip the exercise, record why.
3. **Bucket 13 holds 2 in different families** (`documentation-and-adrs`,
   `research`) — two distinct jobs, no duplication to remove. **Assumption:** keep
   both, no merge, document the reasoning.
4. **Buckets with no duplication to find** (9 and 10 especially, then 3, 8).
   **Assumption:** they return most or all of their inputs, each with a stated
   answer to the removal test. Returning five skills from bucket 9 is a correct
   result; a forced merge there would destroy five distinct capabilities to make
   one number smaller.
