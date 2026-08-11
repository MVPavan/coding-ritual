# Requirements document template

Save as `docs/brainstorms/YYYY-MM-DD-<topic>-requirements.md`.

Every heading below appears in the file. A section with nothing to say gets
"None" — do not delete the heading, because an absent section reads as an
oversight while "None" reads as a decision.

Length follows the work. A small ambiguous ask can fill this in ten lines.

---

```markdown
# <Topic>

Status: draft | approved
Approved by: <who, and when — the explicit approval that named this direction>

## Problem

What is wrong today, for whom, and what changed that makes it worth doing now.
Two or three sentences. Not the solution.

## Recommended direction

The chosen approach and why it beat the alternatives. Name the alternatives that
were considered and lost — a direction with no discarded rivals was not a
decision.

## Design

How it hangs together: the pieces, what each is responsible for, and how they
talk to each other.

If a diagram was agreed during the brainstorm, embed it here as a Mermaid block
— not as a link to a scratchpad file, which will not exist for the next reader.

For each piece, be able to answer:
- what does it do
- how is it used
- what does it depend on
- can its internals change without breaking whatever consumes it

If any of those has no clear answer, the boundary is in the wrong place.

## Behaviour and acceptance

What it does, stated so that someone else can tell whether it happened.

- **Happy path** — given <situation>, when <action>, then <result>
- **Error and edge cases** — what happens on bad input, a missing dependency,
  a partial failure, an empty or oversized case. Silence here means the failure
  behaviour gets invented during implementation.
- **Out of bounds** — behaviour that is explicitly not defined by this document

## Testing

Which seam this is tested at, and why. Prefer a seam that already exists to a
new one, and the highest one that still gives a real signal — the fewer seams a
codebase has, the better.

Name the level (unit, integration, end-to-end), what is exercised for real, and
what is substituted. If existing tests need to change, say which and why.

## Constraints

What is already fixed: existing code, external systems, deadlines, conventions
in this repo that the work has to live inside.

## Assumptions to validate

Each written as the assumption plus how to test it, ranked:

- [ ] **Must be true** — <assumption> — <how to test>
- [ ] **Should be true** — <assumption> — <how to test>
- [ ] **Might be true** — <assumption> — <how to test>

## Scope

What is being built, in full. This is the approved total, not the first slice —
sequencing is `planning`'s decision, made against this.

## Not doing

Each entry with its reason. Deferred and rejected are different — say which.
This section is what stops a decision being re-litigated in three weeks.

- <thing> — <reason> — deferred | rejected

## Open questions

Anything unresolved that needs an answer before or during implementation, and
who can answer it.
```

---

## Why these sections

`prepare-phases` passes this file as `--design` on every epic it creates, so it
is read by people working on tasks that were split out of it long after the
conversation ended.

**Recommended direction**, **Behaviour and acceptance**, and **Not doing** are
the three that survive that gap — they carry the reasoning, the definition of
done, and the rejected alternatives. The rest can usually be reconstructed from
the code; those three cannot.
