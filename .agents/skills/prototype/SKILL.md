---
name: prototype
description: Use when a runnable throwaway experiment can resolve a specific design, state-model, algorithm, or UI question, or before committing to an interaction or architecture with no precedent in the codebase or a product decision that depends on feel.
---

# Prototype

Build a throwaway artifact to answer a named design question. Choose the smallest
runnable form that exposes the uncertainty: a script for algorithms, a state demo
for domain behavior, or a UI mockup for interaction/layout.

State the question and observable success before building. Use the authorized
location, otherwise an isolated scratch artifact. Keep prototypes clearly marked,
reproducible and separate from production behavior. Use synthetic or appropriately
scoped data; retain safety checks and accessibility that the experiment requires.
Skip polish and abstractions that do not help answer the question; keep the error
handling and safety checks needed to run the experiment safely. Name a prototype's
states, actions and labels in the project's domain terms.

- State/logic exploration: `LOGIC.md` offers script and shareable HTML options.
- UI exploration: `UI.md` covers contextual mockups and optional variants.

Persistence, external calls and realistic integration belong only when needed to
answer the question and authorized. A small assertion may be the cheapest proof;
a prototype does not imply either a full test suite or a ban on checks.

Record the outcome, exercised cases, limitations and artifact/run pointer in the
existing task or requested report. An inconclusive experiment is a valid result.
Where no tool here can drive the surface, hand over the pointer, say you have not
observed it, and leave the outcome inconclusive until a person reports.

Building the chosen direction, or promoting code into production, is separate work
requiring its own scope and normal checks. When a build is wanted, at top level
return to `mvp-mode`, where the feature playbook fits; inside a delegated task,
report that route to the parent. Preserve the artifact when it supports the
conclusion; committing, creating production routes and cleanup retain their
authority gates.

## Competing variants

Conditional: when comparing alternatives is the question, build those variants.
When the decision is an interaction or architecture with no precedent in this
codebase, or a product decision whose experience depends on feel (even where a
precedent exists), build two or three competing runnable variants, UI or logic,
and compare them side by side before committing to one.

Put every variant behind one switcher and label each: a UI control, or a flag or
argument for a script. Show the preview pointer and, for variants, the key for each.
Finish with the tradeoffs and one recommendation; the decision stays with whoever
owns it. Record the comparison, the recommendation and any variant chosen with the
outcome.
