---
trigger: A focused structure change that must keep behaviour unchanged, with no settled plan to execute.
traits: [structure-only-gate]   # new
steps:
  - id: refactoring#1
    when: always
    actions: [{trait: behaviour-pin-gate}]   # new
    calls: [{to: "skill:explain-code"}, {to: "skill:tdd", when: no existing check pins the behaviour}]
  - id: refactoring#2
    when: always
    actions: [{trait: branch-deleting-reshape}]   # new
  - id: refactoring#3
    when: always
    actions: [{trait: named-target-shape}]   # new
    calls: [{to: "skill:codebase-design", when: the target crosses a function boundary}]
  - id: refactoring#4
    when: the pin holds
    actions: [{trait: pin-green-moves}, {trait: rename-spot-check}, {trait: implement-against-sketch}]   # the first two new; the third when refactoring#3 sketched
    calls: [{to: "skill:delegation", when: the edits are mechanical}]
  - id: refactoring#5
    when: refactoring#4 changed code
    actions: [{trait: behaviour-equivalence-proof}]   # new
  - id: refactoring#6
    when: refactoring#5 passed
    actions: [{trait: reader-load-keep-or-revert}]   # new
  - id: refactoring#7
    when: every exit
    actions: [{trait: build-closeout}]   # new; shared with feature
  - id: refactoring#8
    when: finished, the proof held and the change was kept, after refactoring#7
    calls: [{to: "skill:land"}]
---

# Refactoring

For a focused structure change that must keep behaviour unchanged, with no settled
plan to execute, including a focused redesign of internals. Changed behaviour is the
feature playbook, and a settled plan to run is `execution`. Staged work across many
modules goes to the multi-phase-plan playbook first when its units or questions are
unsettled, and settled staged work to plan stays `planning`.

**The gate:** the structure changes and the behaviour does not. A bug or missing
feature asked for in the same request is split out first: name it as the next request
through the router and stop. One found on the way stays out of this change: name it
the same way, then finish against the pin with the defect left as it is, or stop when
the moves depend on it.

1. **Pin.** Invoke `explain-code` on the affected subsystem to learn its contract.
   Then capture the current behaviour in a check before any structure moves: a type
   check or a lint does not count. When no existing check pins it, invoke
   `tdd` in characterization mode. When no pin can be made, stop
   and go to step 7.
2. **Name what is missing.** By `principle-model-the-domain`, name the structure the
   code lacks. A reshape counts only if branches or invalid states disappear; drop
   one that only adds indirection.
3. **Name the target.** By `principle-redesign-from-first-principles`, state the module
   layout, the types and the call graph as if built today. When the target crosses a
   function boundary, invoke `codebase-design` for a sketch.
4. **Move.** When the pin holds, apply `principle-subtract-before-you-add`, and
   `principle-migrate-without-shims` only where its own conditions hold. Move in small
   steps, each keeping the pin green. Read every rename against the real files,
   strings and prose included. When step 3 sketched, build against that sketch as the
   contract: surface any departure, and revise the sketch first when the code must
   diverge. When the edits are mechanical, hand them over through `delegation`.
5. **Prove.** On the real artifact, run what shows the behaviour is unchanged. For a
   larger move, diff the old version's output against the new one's. A failure returns
   to step 4.
6. **Keep or revert.** Judge the result by `principle-minimize-reader-load`. When
   reader load did not drop, revert this run's edits.
7. **Close out**, on every exit. Remove temporary scaffolding, name what is unfinished
   in the tree and list the open decisions.
8. **Land.** Only when finished, with the proof held and the change kept, after step
   7: invoke `land`. `principle-sequence-verifiable-units` applies to its split. No
   stopped or reverted path lands.

## Reply

- **Finished:** the structure changed, the pin, the equivalence proof, the change in
  reader load, what was kept and what reverted, that no behaviour is new, anything
  split out, and `land`'s commits or plan, or its refusal and the gap it named.
- **Reverted at step 6:** why, and that the tree is restored.
- **Stopped:** where, and the state of the pin.
- **Split out:** the bug or feature, named as the next request through the router.

Every reply also says what the closeout removed and what it left unfinished.
