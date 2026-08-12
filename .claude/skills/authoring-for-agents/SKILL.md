---
name: authoring-for-agents
description: Use when creating or editing a document an agent consumes — a SKILL.md, AGENTS.md, CLAUDE.md, a rule or command file, or reference material one of them points at. Also use when such a document exists but agents ignore it, misread it, or skip its steps.
---

# Authoring for Agents

A document an agent consumes is behaviour-shaping code, not prose. The
packaging differs — skill, rule, command, pointed-to reference — but the levers
are the same, and so is the goal: predictable behaviour every run, whether that
is the same process, the same routing, or retrieving the same fact.

## Name the failure

Before writing or editing, state what goes wrong without this document, or
with its current version: observed behaviour where you have it, a nameable
risk or an unguessable repo fact where you don't. A discipline rule — one the
agent will be tempted to skip — needs more than a hunch: an observed baseline
(see Verify).

No nameable failure or need means no document. Guidance the model already
follows by default pays context load to say nothing.

## Match the form to the failure

The form that fixes one failure type measurably backfires on another.

| Baseline failure | Right form | Wrong form |
|---|---|---|
| Knows the rule, skips it under pressure | Prohibition + rationalization table + red flags | Soft guidance ("prefer…", "consider…") |
| Complies, but the output has the wrong shape | Positive recipe: state what the output *is* — its parts, in order | Prohibition list ("don't restate…") |
| Omits an element it already produces | A required slot in the template it fills | Prose reminders near the template |
| Behaviour should depend on a condition | Conditional keyed to an observable predicate | Unconditional rule + exemption clauses |

Whichever form you pick: no nuance clauses. "Don't X unless it matters" reopens
the negotiation — a real exception is its own conditional on an observable
predicate, not a softener on the rule.

## Pick the surface

One failure, one surface — the smallest that reaches the agent at the right
moment:

| The fix is… | Surface |
|---|---|
| A guardrail every session must hold | rule under `.claude/rules/` |
| Repo orientation: purpose, read order, verification commands | `AGENTS.md` / `CLAUDE.md` — short, pointing at detail elsewhere |
| A durable repo fact, decision, or verified pattern | `.claude/project/` overlay or learnings |
| A repeated workflow the agent should trigger itself | skill (model-invoked) |
| A workflow only the human starts, or needing their arguments | command, or a user-invoked skill |
| Heavy material only some runs need | a reference file behind a pointer |
| Mechanically checkable (regex, exit code, schema) | a hook or script — automate it, don't document it |

## Write

Route by branch:

- Every authoring task: `references/writing-principles.md` — pointers, the two
  loads, the information hierarchy, degrees of freedom, leading words, pruning.
- Only when the document is a skill or command:
  `references/skill-anatomy.md` — layout, frontmatter, invocation mechanics.
- Only when you reach Verify and the rung calls for it:
  `references/testing-docs.md`.

Four rules too costly to leave behind a pointer:

1. A description states triggers only — never a summary of the workflow.
   Agents follow the summary and skip the body.
2. State the target behaviour, not the banned one. A prohibition earns its
   place only as a hard guardrail you cannot phrase positively — and even then,
   pair it with the positive target.
3. One source of truth per meaning. Do not restate what the environment
   (`--help`, configs, directory layout) already answers.
4. Every sentence must change behaviour versus the default. Delete the ones
   that don't — whole sentences, not trimmed words.

## Verify

Proportional to what the document enforces — methods in
`references/testing-docs.md`. Pick the lowest rung that gives real evidence:

| Change | Minimum bar |
|---|---|
| Small edit to an existing doc | Cold reread + the no-op test on each new sentence |
| New doc, section, or body rewrite | Fresh-context read: a subagent gets the doc and a task that should exercise it — watch what it does; never ask "is this clear?" |
| New or changed description, pointer, rule scope, or command | Packaging test: fresh context with only the normal entry point — does it fire when it should, stay quiet when it shouldn't, and reach the body? |
| Discipline rule the agent will want to skip | Baseline the failure without the doc, then pressure-test with it |

Done when the rung you picked has produced its evidence: a behaviour change
you watched, a trigger that fired and did not misfire, or edits that survive
the no-op test.

## Rules

- Search the existing catalog first; extend the nearest skill or rule instead
  of near-duplicating it.
- Make the result discoverable on its own surface — a skill through its
  description, a command through its name, a durable doc through
  `.claude/project/docs-index.md`. Touch the root read order only for material
  every session needs.
- Match the conventions of the harness you are writing into, not the corpus
  you borrowed from.
