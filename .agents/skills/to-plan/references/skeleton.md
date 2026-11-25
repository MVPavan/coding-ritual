# Skeleton plan

Consulted from `to-plan`'s Skeleton branch. It extends `plan-format.md`: fields keep
their meaning there, and its right-sizing test, placeholder list and self-review
apply. `Evidence:` replaces `Verification:`. How a scope runs is `implement`'s.

## A plan in the form that passes the check

```markdown
# Move the store to the new schema

**Origin:** docs/workstreams/store/roadmap.md, phase 2.
**Goal:** Every read uses the new schema.
**Out of scope:** The export command, which keeps its format.
**Constraints:** Python 3.12; no downtime for readers.

## How to run this

Run with: implement, task scope.
Authority: planning only, so implementation starts on the owner's word.
The coordinator ticks a box only when its evidence exists.

## Tasks

### Task 1: Read rows through the new schema

Goal: `store.load` returns the same rows from either schema.
Files:
- Modify: store/load.py
Approach: Add the new reader beside the old one and pick by the schema version.
Dependencies: None
Evidence:
- [ ] Check: `uv run pytest tests/store -q`. Pass when it exits 0.
- [ ] Live: Run `store show sample` on both fixtures. Pass when the outputs match.
- Measure: n/a: no number is claimed.

## Appendix A. Settled questions

Q0. Can both schemas run side by side? Both readers ran on sample rows; outputs matched.

## Appendix B. Alternatives rejected

Rewriting all rows in one migration: readers would stop during the copy.
```

## Rules

**Sections, in order:** the header, `## How to run this`, `## Tasks`, `## Open questions`
only while one stays open (`Q<n>.` with options and a recommended default), then both
appendices. Further `## Appendix …` sections may follow. An appendix may say `None`.

**Scope.** Name one: task for a standalone plan or single-phase epic; phase when a
roadmap phase names it, and then every task carries `Stage:`; workstream only on an
explicit request to run every remaining phase.

**Tasks.** Each field once, its label starting a line, and no heading inside a task:
`implement`'s brief extractor ends a task at any heading. Number tasks from 1.
`Dependencies:` holds `None` or task numbers. A task a question holds carries
`Blocked by: Q<n>`, and every open question holds a task.

**Evidence, one line per box.** `- [ ] Check:` is required, with a backticked command
and `Pass when`; draw it from `.repo-context/verification.md` when the project has it,
otherwise from its own verification guidance and runnable checks. `- [ ] Live:` drives
the change the way a user reaches it, with `Pass when`; for a CLI that means running
the command. `- [ ] Measure:` has a backticked command, a number and `Pass when`, only
where a number is the claim. Without a box they read `- Live: n/a: <reason>` and
`- Measure: n/a: <reason>`. An end-to-end check out of reach stays a box saying `PARTIAL`.

**One mode.** Task sections give steps; reasons go in the appendices. Appendix A stands
alone, with outcomes written inline, since a scratch artifact stays local.
