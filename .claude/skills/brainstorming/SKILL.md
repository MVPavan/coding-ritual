---
name: brainstorming
description: Use when a piece of work needs its scope and behaviour settled into a spec — the ask is ambiguous, scope and success are unresolved, or decisions were made in conversation but never recorded. Also trigger on brainstorm phrases. To open up a raw idea first, use idea-refine; to interrogate a plan that is already written, use grilling.
---

# Brainstorming

Turns an unsettled ask into an approved spec that this repo's planning chain consumes.

## Ground

Read `CLAUDE.md`, `.claude/project/brief.md`, and `.claude/project/docs-index.md`.
Then scan enough repo context to answer: does something similar already exist, what constraints are already real, which docs are authoritative.

Done when you can name the closest existing thing, or say there is none.

## Route

Answer four questions from the conversation so far. If one cannot be answered, that is itself the answer.

- **Shape** — one piece of work, or several independent subsystems?
- **Intent** — are outcome, user, why now, success, and the binding constraint all known?
- **Direction** — is one approach chosen, or are several still live?
- **Detail** — is the behaviour decided, or only the direction?

Take the first row that matches. When a route returns, answer the four again.

| State | Go to | It comes back with |
|---|---|---|
| Several independent subsystems | decompose, agree the order, restart on the first piece | one piece of work |
| Small, and its behaviour is already explicit | stop — this skill does not apply | — |
| Every decision is already in the conversation | **Converge**, restate only | an approved direction |
| Intent incomplete | **Interview** | complete intent |
| Several directions live, idea ambiguous/complex | the **`idea-refine`** skill | one direction, its bets named in an idea doc |
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

If the direction is already chosen — in the conversation or by an idea doc — skip
the approaches and go straight to the restate. Otherwise present 2-3 approaches
with their trade-offs, leading with the one you recommend and why. Then restate,
one line each:

    Outcome / User / Why now / Success / Constraint / Out of scope

Success is checkable, not an adjective. Out of scope is not optional.

Then get approval that names the direction — "yes, the second one" rather than
assent to the message. Vague agreement is a signal to re-ask as a choice between
two concrete options; `references/interviewing.md` lists the common forms and
what each usually means.

## Write

Fill every section of `references/spec-template.md` and save it to
`docs/specs/YYYY-MM-DD-<topic>.md`, creating the directory if it does not exist.
It opens as `Status: draft`.

Write it every time, not only when the decisions feel durable — `planning`
(Decompose) passes this path as `--spec-id` on every epic. A section with nothing to say gets
"None"; keep the heading. A small ambiguous ask still ends in a document, just a
short one.

If filling a behaviour, acceptance, or testing section would be guesswork, the
behaviour is not decided — interview those gaps first (one question at a time),
then write.

If an idea doc exists (`docs/ideas/<topic>.md`), cite it under *Solution*; the
discarded alternatives and strategic bets stay there. The spec records only
build decisions and exclusions, plus any explicit departure from the idea doc.
Once the spec exists it is authoritative — do not edit the idea doc afterwards.

## Review

Read the file again with fresh eyes:

1. **Placeholders** — any TBD, TODO, or vague requirement? Fix it.
2. **Consistency** — do any two sections contradict each other?
3. **Scope** — one implementation plan, or does it still need decomposing?
4. **Ambiguity** — could a requirement be read two ways? Pick one and say which.

Fix inline; do not re-review. For standard or deep work, have a spawned critic
subagent (model per CLAUDE.md §Independent critique) critique the document
before it reaches the user.

Then ask the user to read the file. Make any changes they ask for and show them
again. Once they accept it, set `Status: approved` and record who approved it —
`planning` needs an approved document, and a draft is not a handoff. A spec with
a blocking open question cannot be approved: resolve it, or move it explicitly
to *Out of Scope* or a deferred follow-up.

## Keep it current

The document stays live for the work it describes. When a decision changes or
scope moves, update it first and then implement — beads epics point at this file
by path, so a stale file misleads every task underneath it.

## Rules

- The approved document is this skill's only artifact — write no code.
- Hand off to `planning` only after the document is approved.
- Needs a live user. Inside an autonomous run, stop and report the underspecified
  ask as a blocker rather than guessing.
