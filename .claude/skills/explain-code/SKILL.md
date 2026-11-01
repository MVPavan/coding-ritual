---
name: explain-code
description: "Use to explain how this repository's code works, why it has its shape, or which option fits, with citations: before changing it, at a playbook step's call, or inside a delegated task. At top level, a question that should end in that answer is the investigation playbook; a single lookup needs neither; an external codebase is codebase-research."
---

# Explain code

The deliverable is one cited answer about this repository's code, enough for the
reader to change that code safely. How it works is the core. Two branches below
add to it, each on its own condition.

Change nothing: no edit, no commit, not even a temporary print or probe. A delegate
you use works under the same limit. If only instrumentation could answer the
question, say so; a failure with an unknown cause is `systematic-debugging`.

## Read

If a target is ambiguous but each reading would give much the same answer, state
the reading you took and carry on.

Fit the reading to the width of the question:

- **Narrow** (one function, one module, one specific question): answer in one pass.
- **Wide** (a subsystem across many files or services): split it into angles
  through delegation by the local rule (the `delegation` skill), then reconcile
  what comes back into one account.

When findings conflict, open the code and let it settle them. Agreement between
reports, or the confidence of one, settles nothing.

## Answer

Use these sections, and drop any that does not apply:

- **Overview:** what this is and what it does.
- **Concepts:** the types and abstractions the rest of the answer relies on.
- **Flow:** the main section. Walk it in prose from what triggers it to what it
  produces, naming the file and function at each step (`path:line`).
- **File map:** where a person starts working on it.
- **Pitfalls:** what would surprise someone changing it.

## Branch: history

**Condition:** the question asks why the code has its shape, what motivated it, or
which change brought a regression and for what reason.

Read `references/history.md` and follow it. Its Answer section replaces the one
above; everything else in this file still holds.

## Branch: decision

**Condition:** the question is a choice between alternatives for this code, and the
scope is settled. Open scope is `brainstorming`; a choice that needs outside
sources is `research`.

Read the code each alternative would touch, then recommend one, with a table of the
tradeoffs. Give it one row per option, and cite what in the code drives each cell.

## Route back

This skill ends at the answer. If a change is wanted, name it as the next request
and do not start it: at top level return to `mvp-mode`; in a delegated task, report
that route to your parent.
