---
name: brainstorming
description: Use when a piece of work needs its requirements settled and written down — the ask is ambiguous, scope and success are unresolved, or decisions were made in conversation but never recorded. To open up a raw idea first, use idea-refine; to interrogate a plan that is already written, use grill-me.
---

# Brainstorming

Turns an unsettled ask into an approved requirements document that this repo's
planning chain consumes.

## Ground

Read `AGENTS.md`, `.claude/project/brief.md`, and `.claude/project/docs-index.md`.
Then scan enough repo context to answer: does something similar already exist,
what constraints are already real, which docs are authoritative.

Done when you can name the closest existing thing, or say there is none.

## Route

Answer four questions from the conversation so far. If one cannot be answered,
that is itself the answer.

- **Shape** — one piece of work, or several independent subsystems?
- **Intent** — are outcome, user, why now, success, and the binding constraint
  all known?
- **Direction** — is one approach chosen, or are several still live?
- **Detail** — is the behaviour decided, or only the direction?

Take the first row that matches. When a route returns, answer the four again.

| State | Go to | It comes back with |
|---|---|---|
| Several independent subsystems | decompose, agree the order, restart on the first piece | one piece of work |
| Small, and its behaviour is already explicit | stop — this skill does not apply | — |
| Every decision is already in the conversation | **Converge**, restate only | an approved direction |
| Intent incomplete | **Interview** | complete intent |
| Several directions live, idea ambiguous/complex | the **`idea-refine`** skill | one direction, its bets named |
| One direction, behaviour undecided | **Converge** | an approved direction |
| Direction approved | **Write** | a draft document |

## Interview

One question at a time, each carrying your best guess and the reasoning behind
it. Be visibly willing to be wrong — a polite user agrees with a confident guess.

Hollow answers, what is not really approval, and the failure modes:
`references/interviewing.md`. A question better drawn than described:
`references/visuals.md`.

Done when you can predict the user's reaction to the next three questions you
would ask, **and** every field of the restate below holds an answer the user
gave rather than one you supplied. If several rounds pass and you still cannot,
say that something foundational is missing and step back.

## Converge

Present 2-3 approaches with their trade-offs, leading with the one you recommend
and why. Then restate, one line each:

    Outcome / User / Why now / Success / Constraint / Out of scope

Success is checkable, not an adjective. Out of scope is not optional.

Then get approval that names the direction — "yes, the second one" rather than
assent to the message. Vague agreement is a signal to re-ask as a choice between
two concrete options; `references/interviewing.md` lists the common forms and
what each usually means.

## Write

Fill every section of `references/requirements-template.md` and save it to
`docs/brainstorms/YYYY-MM-DD-<topic>-requirements.md`, creating the directory if
it does not exist. It opens as `Status: draft`.

Write it every time, not only when the decisions feel durable — `prepare-phases`
passes this path as `--design` on every epic. A section with nothing to say gets
"None"; keep the heading. A small ambiguous ask still ends in a document, just a
short one.

## Review

Read the file again with fresh eyes:

1. **Placeholders** — any TBD, TODO, or vague requirement? Fix it.
2. **Consistency** — do any two sections contradict each other?
3. **Scope** — one implementation plan, or does it still need decomposing?
4. **Ambiguity** — could a requirement be read two ways? Pick one and say which.

Fix inline; do not re-review. For standard or deep work, have a second model
critique the document before it reaches the user.

Then ask the user to read the file. Make any changes they ask for and show them
again. Once they accept it, set `Status: approved` and record who approved it —
`planning` needs an approved document, and a draft is not a handoff.

## Keep it current

The document stays live for the work it describes. When a decision changes or
scope moves, update it first and then implement — beads epics point at this file
by path, so a stale file misleads every task underneath it.

## Rules

- Write no code in this skill.
- Hand off to `planning` or `prepare-phases` only after the document is approved.
- Repo-relative paths only.
- Needs a live user. Inside an autonomous run, stop and report the underspecified
  ask as a blocker rather than guessing.
