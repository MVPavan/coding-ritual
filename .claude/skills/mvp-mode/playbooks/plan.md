---
trigger: "A request to get work ready to build without building it: plan a change or feature, settle its open questions first, split an approved spec into phases, or plan one phase, one change or a batch of units, ending in approved, tracked planning documents."
traits: [planning-run-gate]   # new; replaces plan-only-gate
steps:
  - id: plan#1
    when: always
    actions: [{trait: small-change-plan-skip}]
  - id: plan#2
    when: plan#1 did not skip
    calls: [{to: "skill:delegation", when: "the router's delegation rule sends the exploring to a subagent, in its explorer role"}]
  - id: plan#3
    when: exploring left a question whose answer changes the plan
    actions: [{trait: settle-by-observation}]
    calls: [{to: "skill:discovery", when: "a material scope, behaviour, dependency or authority choice no run settles is open"}, {to: "skill:prototype", when: a run can observe the answer}]
  - id: plan#4
    when: plan#1 did not skip and no open decision holds up every task
    actions: [{trait: plan-route-by-shape}]   # new
  - id: plan#5
    when: "plan#4 needs a spec: a durable spec was asked for, or several phases have no approved multi-phase spec"
    calls: [{to: "skill:to-spec"}]
  - id: plan#6
    when: plan#4 chose several phases, and the spec is approved
    calls: [{to: "skill:to-roadmap", when: "whole: its own approval of the structure, then its tracker seed"}]
  - id: plan#7
    when: "plan#4 chose one piece: one phase, one change, or a batch of units"
    calls: [{to: "skill:to-plan", when: "its Skeleton branch when the units run box by box with evidence per unit, otherwise Elaborate; this one whole call stays open through plan#9"}]
  - id: plan#8
    when: the roadmap or plan is approved (a recorded approval counts) and nothing has recorded it in Beads yet
    calls: [{to: "skill:tracker"}]
  - id: plan#9
    when: plan#5, plan#6 or plan#7 wrote a document, a draft spec awaiting approval included
    calls: [{to: "skill:unslop", when: "on the sections a person reads, leaving task fields, stage acceptance and requirement lines as they are"}]
  - id: plan#10
    when: every exit
    actions: [{trait: planning-run-closeout}]   # new; replaces plan-only-closeout
  - id: plan#11
    when: after plan#10, when this run wrote tracking files and the owner's commit authority covers them
    calls: [{to: "skill:land", when: "the tracker's export and renders only"}]
---

# Plan

For a request to get work ready to build without building it: plan a change or
feature, settle its open questions first, split an approved spec into phases, or plan
one phase, one change or a batch of units. A build with no plan needed is the feature
playbook (or refactoring, bug-fix); settled, tracked work to run is `implement`. A
request for only a spec is `to-spec`, and for only decisions `discovery`; decisions
that depend on each other across sessions are `/wayfinder`.

**The gate:** the run ends at its planning documents and implements nothing. It
writes only:
- the documents its steps produce: a discovery record, a spec, a roadmap or a plan;
- `docs/discovery/INDEX.md`, when step 3's `discovery` call writes its record under
  `docs/discovery/` and so regenerates that index;
- gitignored scratch;
- tracker writes made under approval, with their export and renders.

It leaves what was already dirty as found. Before step 1, note `git status --short`
and a checksum of each path already dirty. A path already dirty, the index included,
is checked by its checksum, and named if anything but this run's allowed writes
changed it.

1. **Skip.** When the change is a file or two and how to make it is plain, and no plan
   file was asked for, say so and go to step 10.
2. **Explore.** Read what the plan will touch. When the router's delegation rule sends
   this to a subagent, invoke `delegation` in its explorer role, and brief it to return
   where the code starts, the files that matter, the local conventions and how it is tested.
3. **Settle.** Sort each question whose answer changes the plan:
   - A run can observe the answer: invoke `prototype`, naming the plan's Appendix A as
     its report. A recommendation from variants is evidence: take it when the choice is
     routine and ask when it is material.
   - A routine choice no run settles: decide it and record it in Appendix B.
   - A material scope, behaviour, dependency or authority choice no run settles, or an
     inconclusive prototype on one: invoke `discovery`, which asks the owner with
     options and a recommendation.

   Asking does not stop the plan. Tasks that do not depend on the answer are written,
   and those that do carry `Blocked by:`. When every task waits on it, write no plan
   and go to step 10.
4. **Route.** Name the work's shape. Several phases means each phase has an
   independently checkable exit, the rule `to-roadmap` and `to-plan` state in their
   opening paragraphs. A roadmap phase, one change, or a person's batch of units is
   one piece. A durable spec asked for, or several phases with no approved multi-phase
   spec, goes to step 5 first. Then several phases go to step 6, and one piece to step 7.
5. **Spec.** Invoke `to-spec`; its approval gate decides. Without approval, skip
   steps 6-8, run step 9 on the draft spec, then step 10, and give the "Spec written,
   awaiting approval" reply. With approval given in this run, go on as step 4 chose.
6. **Roadmap.** Invoke `to-roadmap` whole: its own approval of the structure, then its
   `tracker` seed. The run plans no further than the roadmap. Later phase plans are written just in
   time, as each phase runs under `implement`, so this run does not plan the first
   phase too.
7. **Plan.** Invoke `to-plan` whole: its Skeleton branch when the units run box by box
   with evidence per unit, otherwise Elaborate. This one whole call stays open through
   step 9. `principle-sequence-verifiable-units` applies: one task, one change with its
   own evidence. When `to-plan` takes its no-document branch (a roadmap phase whose
   acceptance already says enough), step 8 skips, and step 9 skips unless step 5
   wrote a spec in this run, which it still edits; the reply says so.
8. **Track.** `to-roadmap` and `to-plan` invoke `tracker` themselves once the work is
   approved. When that happened inside their call, this step is
   `skip: recorded by <callee>`, so nothing is seeded twice. When the approval (a
   recorded approval counts) arrives after the callee returned, and nothing has
   recorded the work in Beads yet, invoke `tracker` here.
9. **Edit for readers.** When step 5, 6 or 7 wrote a document, a draft spec awaiting
   approval included, invoke `unslop` on the sections a person reads: a plan's header
   narrative, `## Open questions` and the appendices, and the prose of a spec or
   roadmap. Its brief says to leave task fields, stage acceptance and requirement
   lines as they are. The Skeleton branch's lint then reruns.
10. **Close out**, on every exit. Compare `git status --short` with the start, and for a
    path already dirty its checksum with the one you noted. Only the documents this run
    wrote (a discovery record's index included), the tracker's export and renders, and
    ignored scratch may differ; name anything else in the reply. This run commits
    nothing except through step 11: committing the planning documents is the next
    request.
11. **Land tracking.** After step 10, only when this run wrote tracking files and the
    owner's commit authority covers them: invoke `land` on the tracker's export and
    renders only. The planning documents stay uncommitted.

## Reply

- **Skipped** (step 1, or `to-plan`'s no-document branch): no plan, why, and the change
  named as the next request, with the path of any spec step 5 wrote in this run. With implementation already authorized, it ends with the
  continuation below.
- **Stopped, decisions open:** the discovery record's path, and the index if written;
  each open question with its options and recommendation; the reply needed.
- **Spec written, awaiting approval:** the spec's path, `Status: draft`, the blocking
  questions, and the approval that lets the run go on. No continuation, whatever build
  authority was given.
- **Roadmap written, awaiting approval or unseeded:** the roadmap's path and the
  approval or tracking it waits for. No continuation.
- **Roadmap written, approved and seeded, planning only:** the roadmap's path, the epic
  and stage IDs. Execution starts on the owner's word.
- **Roadmap written, approved and seeded, implementation already authorized:** the
  same, ending "continuing under `implement`, <the execution scope actually authorized:
  one phase, or the phases named>"; then return to `mvp-mode`, which picks `implement`
  at that scope with no second question: Phase for one named phase, Workstream only
  for an explicit request to run all remaining phases.
- **Plan written, planning only:** the plan's path, uncommitted, so lost if the worktree goes;
  tasks with their dependencies; the named scope; what prototypes proved and what stays
  unproven; the lint's last output and that it proves structure only. Execution starts
  on the owner's word.
- **Plan written, implementation already authorized:** the same, ending "continuing under
  `implement`, <scope>"; then return to `mvp-mode`, which picks `implement` with no
  second question.
- **Plan written, blocked:** the same, with each `Q<n>`, its options and recommendation, the
  tasks that wait and the reply needed.
- **Not written, every task waits:** the question and what was settled so far, with
  Appendix A's content in the reply, since there is no file.
- **Plan written, not ready:** the lint output that remains, and the plan named as not ready.

Every reply also names the Plan playbook and the shape step 4 chose, the steps
skipped, the tracker IDs written and what step 11 committed, and what closeout found
and the scratch files kept.
