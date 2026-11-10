---
name: brainstorming
description: Use when material scope or behavior decisions are still open and need exploring, or the user requests brainstorming. Skip writing settled decisions up as a spec, which is to-spec; handle a single routine ambiguity directly.
---

# Brainstorming

Resolve material scope or behavior decisions before committing to an approach.

## Route before grounding

- Clear, bounded behavior: return to the task; no interview or spec is required.
- One routine missing detail: infer from relevant code or ask one focused
  question, then continue independent work.
- Several live directions: use `references/exploration.md` when structured
  divergence would help.
- Requested interview: use the grilling skill. A written critique is a review,
  not automatic permission to interview or edit documents.
- Decisions already settled: do not reopen them; a durable spec of them is
  `to-spec`.

Read only the relevant existing code, authoritative docs and constraints needed
to distinguish the live choices. Name the closest existing solution before
proposing a new one.

## Resolve

Establish outcome, intended user, success criteria, constraints and exclusions.
Present materially different options with tradeoffs when alternatives remain.
Ask about consequential unresolved choices; group independent questions when
that is easier to answer. Carry prior decisions and authorization forward.
For interview technique or an explanation that benefits from a picture, consult
`references/interviewing.md` or `references/visuals.md`, respectively.

Stop exploring when a direction and its acceptance criteria are sufficient for
the next authorized step. Do not invent more questions or variants to fill a quota.

## Hand off

An in-chat decision is enough for bounded work. When a durable spec is wanted
for planning or another session, hand the decisions to `to-spec`. Report a
direction still unresolved as a blocker to whoever started the brainstorm.

This skill's output is decisions. Continue into `to-spec`, `planning` or
`implement` when already authorized; a brainstorming-only request does not
authorize code changes.
