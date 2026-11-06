---
trigger: New behaviour to design and build, with no settled plan to execute.
traits: [lead-owns-design, contested-design-gate]   # new
steps:
  - id: feature#1
    when: always
    calls: [{to: "skill:explain-code"}]
  - id: feature#2
    when: the change crosses a function boundary, two shapes pass the two-shape test, or a person asked for a council
    calls: [{to: "skill:model-council", when: "a person asked for a council; its branch delivers the sketch"}, {to: "skill:codebase-design", when: "no council was asked for; with two shapes it compares them by design-it-twice and recommends one"}]
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
    when: a dispute by the dispute test is open after feature#5
    calls: [{to: "skill:interrogate", needs: [run-proven-finding], when: "a verified finding against the design returns to feature#2 and one against the build to feature#4"}]
  - id: feature#7
    when: every exit
    actions: [{trait: build-closeout}]   # new
  - id: feature#8
    when: finished and verified with no open dispute, after feature#7
    calls: [{to: "skill:land"}]
---

# Feature

For new behaviour to design and build, with no settled plan to execute. A plan or
roadmap phase to run is `implement`. A build whose units or questions are unsettled
goes to the multi-phase-plan playbook first, and settled work to plan stays `planning`.

**The gate:** the lead settles the design and reviews the result, whoever writes the
code. This playbook does not call `implement`, so a Feature build keeps no run
ledger. A council runs only when a person asks; this playbook never starts one. Each
step runs whatever the change's size; a step whose condition is false stays
`skip: <reason>`.

**Two-shape test.** Two shapes means you can write, in one sentence each, two shapes that
both meet the brief and differ materially to a caller, in behaviour or in maintenance cost,
and neither the brief, the code's existing pattern nor a principle already picks one.
Naming, ordering and style are one shape. If you cannot, you have one shape. A delegate
returning with shapes writes the same two sentences; if they fail, the lead chooses and
goes on.

**Dispute test.** A real dispute: someone other than the lead (the user, a delegate, a
reviewer, or a document the request names) has stated a specific failure the design would
cause or a specific alternative it should have taken, with a reason; a run could test it;
and evidence in hand does not settle it. The lead's own doubt never fires it: the lead
resolves that itself and says so. The reply quotes the objection and who raised it. Being
small waives nothing.

1. **Explain.** Invoke `explain-code` on the affected subsystem.
2. **Design.** A person's request for a council comes first, whatever the shapes: its rows
   below decide. With none, one clear shape across a function boundary: invoke
   `codebase-design` for a sketch, with no comparison. Anything else: this table decides.

   | What happens | Feature does | Reply says |
   |---|---|---|
   | Two shapes, no council asked for | `codebase-design` compares them by design-it-twice and recommends one; the lead picks; on to step 3 | what was chosen and why, and that a council is available |
   | A person asks for a council in the conversation; a "yes" in words counts | Invoke `model-council`, pick-and-graft branch. Its sketch is this step's result; on to step 3 | base, grafts, members |
   | The council ends with no artifact | Go to step 7 and stop, candidates kept, no solo sketch in their place. A person's next message resumes here | why it ended, candidates' paths |
   | A council asked for after the build | Back to this step with the council; later steps rerun as needed | that the built work may be redone |
   | The person names a shape | That shape, sketched; on to step 3 | "your pick; no council" |
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
6. **Dispute.** When a dispute by the dispute test is open, invoke `interrogate`:
   adversaries try to break the design and only a run counts. A verified finding against
   the design returns to step 2, and one against the build to step 4. After a fix, rerun the
   proven commands; new adversaries only when step 2 changed the design. After two rounds
   with a finding still open, stop with the state, and cite `principle-attack-the-premise`.
   Test false: no `interrogate`; quote an objection a run cannot test or evidence settles,
   with who raised it and why it did not fire, and list it as an open decision. A person
   withdrawing a dispute, the lead accepting and fixing it, or a replayed run that tested
   the claim and passed closes it, for the snapshot: a path in scope changed since needs a
   rerun to land. Otherwise it stays open (`interrogate` not running, no run reaching the
   claim, a failure not reproduced or not replayable): go to step 7; this does not land.
7. **Close out**, on every exit. Remove temporary scaffolding, including `interrogate`'s
   copies once its result is ruled on, name what is unfinished in the tree and list the
   open decisions. A council's candidates are no scaffolding.
8. **Land.** Only when finished and verified with no open dispute, after step 7: invoke `land`.
   `principle-sequence-verifiable-units` applies to its split. No stopped or unverified
   path lands.

## Reply

- **Finished:** what was built, the design path (sketch, design-it-twice or council), what
  was chosen and why, and step 2's reply where its table applies, the checkpoint, the
  proof, the open decisions, a table for any alternatives, and `land`'s commits or plan, or
  its refusal and the gap it named.
- **Stopped at step 2 or 4:** the sketch or diff state (an empty council: why it ended and
  the candidates' paths), and what is needed to continue.
- **Stopped at step 6:** the objection, why it could not be tested or which finding stands,
  and what is needed.
- **Verification incomplete:** the change, and which surface was unavailable or
  inconclusive.

Every reply also names Feature, says what the closeout removed and what it left unfinished,
gives each skipped step with its reason, and quotes any dispute with who raised it.
