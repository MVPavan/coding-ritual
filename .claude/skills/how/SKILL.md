---
name: how
description: "Use to explain how something in this project works now (code, a script, config, a documented process or record format), with citations, or which option fits it once the scope is settled: before changing it, at a playbook step's call, or inside a delegated task. Why it has its shape or what motivated a change is why. At top level, a question that should end in that answer is the investigation playbook; a single lookup needs neither; an external codebase is codebase-research."
---

# How

The deliverable is one cited answer about how something in this project works:
its code, scripts, configuration, documents, decisions or tracker records. Make it
enough for the reader to change that thing safely. The decision branch below adds
to it on its own condition.

Change nothing: no edit, no commit, not even a temporary print or probe. A delegate
you use works under the same limit. If only instrumentation could answer the
question, say so; a failure with an unknown cause is `systematic-debugging`.

Why it has its shape, what motivated it, or which change brought a regression is
`why`. A question that asks both how and why runs this skill, then `why`.

## Read

If a target is ambiguous but each reading would give much the same answer, state
the reading you took and carry on.

Fit the reading to the width of the question:

- **Narrow** (one function, one module, one document, one specific question):
  answer in one pass.
- **Wide** (a subsystem across many files or services): split it into angles
  through delegation by the local rule (the `delegation` skill), then reconcile
  what comes back into one account.

When findings conflict, open the code or artifact itself and let it settle them.
Agreement between reports, or the confidence of one, settles nothing.

## Answer

Use these sections, and drop any that does not apply:

- **Overview:** what this is and what it does.
- **Concepts:** the types and abstractions the rest of the answer relies on.
- **Flow:** the main section. Walk it in prose from what triggers it to what it
  produces, naming the file and function (or section) at each step (`path:line`).
- **File map:** where a person starts working on it.
- **Pitfalls:** what would surprise someone changing it.

## Branch: decision

**Condition:** the question is a choice between alternatives for this project, and
the scope is settled. Open scope is `discovery`. When the choice needs outside
sources, get that evidence from `research` and keep the choice here.

Read what each alternative would touch, then recommend one, with a table of the
tradeoffs. Give it one row per option, and cite what in the project drives each cell.

## Route back

This skill ends at the answer. If a change is wanted, name it as the next request
and do not start it: at top level return to `mvp-mode`; in a delegated task, report
that route to your parent.
