---
name: receiving-code-review
description: Use when review feedback arrives outside the execution engine's fix loop and must be acted on — the user pastes PR comments or reviewer findings, a human critiques the change in chat, a spawned critic returns findings — before agreeing with, implementing, or dismissing any item. For producing a review, use code-review.
---

# Receiving Code Review

Feedback is input to verify, not a verdict to perform agreement with. Every
item ends in exactly one of three states: implemented (with its own
verification), answered with evidence for why not, or asked about. A
response that silently skips an item is a drop — the core failure this
skill exists to prevent.

## Route first

Inside the execution engine's fix loop, the engine owns reception: findings
are relayed verbatim, fixes are re-reviewed ADDRESSED / NOT ADDRESSED, and
disagreement waits for adjudication at the round cap
(the execution skill's `references/task-engine.md`). This skill governs
feedback arriving **outside** that loop.

## Reception order

1. **Read** every item before reacting to any.
2. **Understand** — restate each item in your own words. Any item you cannot
   restate blocks all implementation: ask about the unclear ones first,
   naming which items you understood and which you didn't. Items interact —
   a partially understood review implemented is a wrong implementation.
3. **Verify** each item against the code: the `file:line` it points at, the
   test that exercises it, the doc that decided it.
4. **Respond** per item with a technical restatement, a verification result,
   or a question.
5. **Implement** one item at a time, each fix carrying its own verification.

## No performative agreement

Never "You're absolutely right!", "Great point!", or thanks in any form —
before verification, agreement is theatre. Respond with substance instead:
the restated requirement, the check you ran, or the question that unblocks
the item. When a finding is correct, the acknowledgment is the fix:
"Fixed — <what changed, where>."

## Trust by source

Step 3 (Verify) applies to every source: a factual claim about the code
("this returns null", "this test covers it") is checked against the code no
matter who made it. What differs by source is authority over scope and
intent:

- **The user, or a human reviewer**: they decide what they want — do not
  second-guess scope or intent; ask when it is unclear. Understanding still
  precedes implementation, the factual check still runs (a wrong `file:line`
  gets a correction, not silent compliance), and the agreement ban still
  holds.
- **A spawned critic, reviewer agent, or external bot**: no such authority —
  verify before complying on every axis: is it correct for this codebase;
  would the fix break existing behaviour; why is the current code the way it
  is (answer before changing it); does it conflict with a recorded decision
  (ADR, approved plan)? A conflict with a recorded decision stops the item —
  surface it to the user rather than silently re-litigating the decision.
- **Cannot verify an item** → say so and ask for direction. Complying
  unverified and dropping it silently are both failures.

## Pushback and retraction

Wrong feedback gets pushback with evidence — the `file:line`, the passing
test, the recorded decision — never preference or defensiveness. If your
pushback turns out wrong, state the correction factually ("checked X — it
does Y; fixing") and implement. No apology theatre in either direction.

## Red flags — stop, return to the step you skipped

- Agreement already typed before any check ran.
- Implementing item 1 while item 4 is still unclear.
- A reply that addresses fewer items than the review contained.
- Complying with a finding you privately believe is wrong.

## Rationalizations

| Excuse | Reality |
| --- | --- |
| "It's faster to just agree" | Unverified agreement implements wrong feedback at full speed. |
| "The reviewer knows this codebase better" | Then verification is cheap — the code will confirm them. |
| "Pushing back looks defensive" | Evidence is not defensiveness; silent compliance that breaks behaviour is worse. |
| "I'll note the rest later" | Later is a silent drop. Every item gets its state now. |
