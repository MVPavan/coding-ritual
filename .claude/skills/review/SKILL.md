---
name: review
description: Use for a critic review of any artifact, substantive code review, or to verify and act on review findings. Routine final diff inspection is not a separate review workflow.
---

# Review

Routine final diff inspection follows AGENTS.md without requiring this workflow.

## Critic review

A critic is an independent reviewer, never the author; the user chooses its model.
Give a thorough opinion, then every finding with its severity and supporting
evidence; for code, cite `file:line`. The coordinator filters by severity afterward.
`APPROVE` means no open BLOCKER or MAJOR; otherwise `REVISE`. APPROVE covers only
what was verified; list unverified requirements, never approve them. For a
non-code artifact, the critic receives the artifact and its purpose.

## Severity

Severity follows consequence: BLOCKER for severe safety/data-loss or operational
failure; MAJOR for acceptance or correctness issues blocking trust; MINOR for
nonblocking improvements. Preference alone is not a finding. When the plan or
brief mandates what this review calls a defect, report it as MAJOR, labelled
plan-mandated; the user decides.

## Select a mode

- Code (`inline`, `spec`, `quality`, `re-review`): `references/code.md`; dispatched
  reviewers and structured re-reviews also use `references/review-contract.md`.
- `feedback`: verify and act on incoming findings within authorization, using
  `references/feedback.md`. Producing a review is read-only, whereas applying
  feedback requires implementation authority.
