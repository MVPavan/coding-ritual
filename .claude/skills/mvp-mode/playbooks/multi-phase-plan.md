---
trigger: A request to produce a plan for several independently verifiable units, or work whose open questions must be settled before planning, with no settled plan yet.
traits: [plan-only-gate]   # new
steps:
  - id: multi-phase-plan#1
    when: always
    actions: [{trait: small-change-plan-skip}]   # new
  - id: multi-phase-plan#2
    when: multi-phase-plan#1 did not skip
    calls: [{to: "skill:delegation", when: "the router's delegation rule sends the exploring to a subagent, in its explorer role"}]
  - id: multi-phase-plan#3
    when: exploring left a question whose answer changes the plan
    actions: [{trait: settle-by-observation}]   # new
    calls: [{to: "skill:prototype", when: a run can observe the answer}]
  - id: multi-phase-plan#4
    when: multi-phase-plan#1 did not skip and no open question holds up every task
    calls: [{to: "skill:planning", when: "its Skeleton branch; this one whole call stays open through multi-phase-plan#5"}]
  - id: multi-phase-plan#5
    when: multi-phase-plan#4 wrote a plan file
    calls: [{to: "skill:prose-pass", when: "on the sections a person reads, leaving task fields as they are"}]
  - id: multi-phase-plan#6
    when: every exit
    actions: [{trait: plan-only-closeout}]   # new
---

# Multi-phase plan

For a request to produce a plan for several independently verifiable units, or work
whose open questions must be settled before planning. A request to build is the feature
playbook, which sends unsettled work here first. An existing roadmap phase, an approved
spec to split or a settled plan keeps its route: `planning` or `execution`.

**The gate:** the run ends at the plan and implements nothing. It writes only the plan
file, gitignored scratch, and authorized tracker metadata with its export, leaving what
was already dirty as found. Before step 1, note `git status --short` and a checksum of
each path already dirty.

1. **Skip.** When the change is a file or two and how to make it is plain, and no plan
   file was asked for, say so and go to step 6.
2. **Explore.** Read what the plan will touch. When the router's delegation rule sends
   this to a subagent, invoke `delegation` in its explorer role, and brief it to return
   where the code starts, the files that matter, the local conventions and how it is tested.
3. **Settle.** Sort each question whose answer changes the plan:
   - A run can observe the answer: invoke `prototype`, naming the plan's Appendix A as
     its report. A recommendation from variants is evidence: take it when the choice is
     routine and ask when it is material.
   - A routine choice no run settles: decide it and record it in Appendix B.
   - A material scope, dependency or authority choice no run settles, or an inconclusive
     prototype on one: ask the owner, with options and a recommendation.

   Asking does not stop the plan. Tasks that do not depend on the answer are written,
   and those that do carry `Blocked by:`. When every task waits on it, write no file
   and go to step 6.
4. **Write.** Invoke `planning`, its Skeleton branch; this one whole call stays open
   through step 5. `principle-sequence-verifiable-units` applies: one task, one change
   with its own evidence.
5. **Edit for readers.** When step 4 wrote a plan file, invoke `prose-pass` on the
   sections a person reads: the header's narrative, `## Open questions` and the
   appendices. Its brief says to leave task fields as they are. The Skeleton branch's
   lint then reruns.
6. **Close out**, on every exit. Compare `git status --short` with the start, and for a
   path already dirty its checksum with the one you noted. Only the plan file, the
   tracker's export and ignored scratch may differ; name anything else in the reply.
   This run commits nothing: committing the plan is the next request.

## Reply

- **Skipped:** no plan, why, and the change named as the next request.
- **Written, planning only:** the plan's path, uncommitted, so lost if the worktree goes;
  tasks with their dependencies; the named scope; what prototypes proved and what stays
  unproven; the lint's last output and that it proves structure only. Execution starts
  on the owner's word.
- **Written, implementation already authorized:** the same, ending "continuing under
  `execution`, <scope>"; then pick it with no second question.
- **Written, blocked:** the same, with each `Q<n>`, its options and recommendation, the
  tasks that wait and the reply needed.
- **Not written, every task waits:** the question and what was settled so far, with
  Appendix A's content in the reply, since there is no file.
- **Written, not ready:** the lint output that remains, and the plan named as not ready.

Every reply also names what closeout found and the scratch files kept.
