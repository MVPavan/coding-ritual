---
trigger: New behaviour to design and build, with no settled plan to execute.
traits: [lead-owns-design]   # new
steps:
  - id: feature#1
    when: always
    calls: [{to: "skill:explain-code"}]
  - id: feature#2
    when: the change crosses a function boundary, or a delegate returned with several valid shapes
    calls: [{to: "skill:codebase-design"}]   # INTERIM: batch 3 binds candidates-judge for several valid shapes
  - id: feature#3
    when: always
    actions: [{trait: throughput-checkpoint}]   # new
  - id: feature#4
    when: always
    actions: [{trait: build-brief-shape}, {trait: implement-against-sketch}, {trait: shared-fix-ported}]   # the first and third new; the second when feature#2 sketched
    calls: [{to: "skill:delegation", when: the router's delegation rule sends the code-writing to a subagent}, {to: "skill:review", when: feature#2 ran}]
  - id: feature#5
    when: feature#4 changed code
    actions: [{trait: matching-surface-verify}]   # new
  - id: feature#6
    when: the design is contested
    calls: [{to: "skill:review"}]   # INTERIM: batch 3 binds adversarial-review
  - id: feature#7
    when: every exit
    actions: [{trait: build-closeout}]   # new
  - id: feature#8
    when: finished and verified, after feature#7
    calls: [{to: "skill:land"}]
---

# Feature

For new behaviour to design and build, with no settled plan to execute. A plan or
roadmap phase to run is `execution`. A build whose units or questions are unsettled
goes to the multi-phase-plan playbook first, and settled work to plan stays `planning`.

**The gate:** the lead settles the design and reviews the result, whoever writes the
code. This playbook does not call `execution`, so a Feature build keeps no run
ledger, and it does not start `model-council`: the user may ask for a council at
step 2.

**Interim bindings, until batch 3.** Steps 2 and 6 run on weaker stand-ins, and a
finished reply names the ones it used. Batch 3 binds `candidates-judge` to step 2's
several valid shapes and `adversarial-review` to step 6.

1. **Explain.** Invoke `explain-code` on the affected subsystem.
2. **Design.** When the change crosses a function boundary, or a delegate returned
   with several valid shapes, invoke `codebase-design` for a sketch. Interim: several
   valid shapes use its design-it-twice option, which a clear shape does not need.
3. **Checkpoint.** Write four todo items, each with its answer. An item that does not
   apply stays, as `n/a: <reason>`.
   - **Blocking first:** what must run before any parallel work.
   - **Independent work:** which files, services or layers can proceed at once, and
     which writes must run one at a time.
   - **Shared state:** apply `principle-separate-before-serializing-shared-state`.
   - **Smallest safe split:** the fewest workers that work; if one is best, say why.
4. **Build.** Write the brief first, wherever the code gets written: it names the
   paths, the data shape and the success criteria, and
   `principle-model-the-domain` picks that shape before any logic exists. By the
   router's delegation rule, hand the code-writing over through `delegation`. A
   delegate that meets several valid shapes, such as error-handling or test-structure
   choices inside one function, returns to step 2 and does not choose alone. When step
   2 sketched, build against that sketch as the contract: surface any departure, and
   revise the sketch first when the code must diverge. Port a fix to shared code to
   every consumer and verify each one. When step 2 ran, invoke `review` on the result.
5. **Verify.** Run the change on the surface where it will be used. An inconclusive
   result, or a pass on another surface, is not a pass. A failure returns to step 4.
   When the matching surface is unavailable or the result stays inconclusive, say so
   and go to step 7.
6. **Contested design.** When the design is contested, invoke `review`. Interim: a
   `review` critic stands in for the adversarial review. A finding against the design
   returns to step 2, and one against the build to step 4.
7. **Close out**, on every exit. Remove temporary scaffolding, name what is unfinished
   in the tree and list the open decisions.
8. **Land.** Only when finished and verified, after step 7: invoke `land`.
   `principle-sequence-verifiable-units` applies to its split. No stopped or unverified
   path lands.

## Reply

- **Finished:** what was built, what was chosen and why, the checkpoint, the proof, the
  open decisions, a table for any alternatives, the interim bindings used, and `land`'s
  commits or plan, or its refusal and the gap it named.
- **Stopped at step 2, 4 or 6:** the sketch or diff state, and what is needed to continue.
- **Verification incomplete:** the change, and which surface was unavailable or
  inconclusive.

Every reply also says what the closeout removed and what it left unfinished.
