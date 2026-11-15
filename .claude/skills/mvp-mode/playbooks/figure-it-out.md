---
trigger: A large migration, an ambitious multi-part change or long work a person reviews after stepping away, to work out and carry through, that no narrower playbook fits.
traits: [design-workflow-before-code]
steps:
  - id: figure-it-out#1
    when: always
    actions: [{trait: phase-todos}, {trait: principles-first-todo}]
  - id: figure-it-out#2
    when: always
    actions: [{trait: framing-before-run}, {trait: falsifiable-done-predicate}, {trait: quantified-scope-with-blockers}, {trait: rigor-biased-high-by-reversibility}, {trait: rigor-means-gates-and-artifacts}, {trait: framing-and-tradeoffs-shown}]
  - id: figure-it-out#3
    when: the framing is stated
    actions:
      - {trait: landable-units-or-named-group}
      - {trait: riskiest-unknown-first}             # T5: follows sealed row 2026-11-06-batch-p1:237, largest unknown first only where dependencies allow; logged in .repo-context/unit-kinds.md §5
      - {trait: scaffold-first}
      - {trait: harness-with-pre-change-baseline}   # T5: follows sealed row 2026-11-06-batch-p1:239, builds the check first only when it does not exist yet; logged in .repo-context/unit-kinds.md §5
      - {trait: alternatives-compared-on-one-way-doors}
      - {trait: fan-out-across-seams-only}
      - {trait: worktree-or-branch-per-worker}
      - {trait: written-phase-list-for-review}
      - {trait: designed-steps-as-todos}
    calls: [{to: "skill:codebase-design", when: "a design choice that cannot be undone, not mechanical and not already settled, has materially different alternatives"}]
  - id: figure-it-out#4
    when: the design is written; this one whole call stays open through figure-it-out#6
    actions: [{trait: rolling-log-rows}]
    calls: [{to: "skill:decision-trail"}]
  - id: figure-it-out#5
    when: once per designed unit, in the designed order
    actions:
      - {trait: one-checkpoint-unless-told-not-to}
      - {trait: hypothesis-per-unit}
      - {trait: smallest-evidenced-change}
      - {trait: keep-or-revert-on-predicate}
      - {trait: verified-unit-sequence}
      - {trait: too-easy-pass-suspicion}
      - {trait: judge-paired-with-delegation}
      - {trait: bounded-gate-gaming-retry}
      - {trait: fix-wrong-gate-separately}          # T5: follows sealed row 2026-11-06-batch-p1:255, fixes a wrong gate in its own change within authority, or else reports it; logged in .repo-context/unit-kinds.md §5
      - {trait: three-value-verdict}
      - {trait: no-hidden-negatives}
    calls: [{to: "skill:delegation", when: a unit goes to a worker}, {to: "skill:review", when: a delegated unit's judge is a critic}]
  - id: figure-it-out#6
    when: every exit
    actions: [{trait: whole-result-on-real-product}, {trait: designed-run-reply-fields}]
---

# Figure it out

For a large migration, an ambitious multi-part change or long work a person will review after
stepping away, which the person asks you to work out and carry through yourself, when no narrower
playbook fits. Getting work ready without building it is plan, settled tracked work is implement,
and driving one checkable condition by repeated attempts is autonomous-run.

**The gate:** the design is the first deliverable. Write no code until the designed steps are
written down in step 3. Nothing here commits: committing is the person's call, through `land`.

1. **Principles.** These six steps are the run's phases: the router's rule for running a playbook
   has already put them on the todo list, one item each, before any other todo, so this step is
   its first item. Read the router's Principles lines and open only the principles whose
   situation holds.
2. **Frame.** Ground first: read the code and records the work touches. Do not start the run until
   you can state its framing:
   - Done, as a predicate that could come out false, with the command and its result, or the
     artifact, that checks it. With no predicate that could fail, ask the person: Not started.
   - State the scope in rough units and effort, with the blockers grounding found.
   - The rigor level: start high, raise it for one-way doors and wide impact, lower it for
     reversible low-stakes steps, and still match it to consequences as `AGENTS.md` asks.
   - For a risky step, name the gate or artifact that makes it safer; being more careful is not a
     plan step.

   Show the person the framing and its tradeoffs before the run starts. Showing it is no stop:
   independent work goes on.
3. **Design.**
   - Split the work into units that can each land alone, or into a declared group where
     intermediate states cannot stay green; `principle-sequence-verifiable-units` keeps such a
     group as one unit.
   - Where dependencies allow, order the units so the largest unknown comes first.
   - Sequence the work every later unit benefits from, including its verification, before
     features.
   - When a change needs a check that does not exist yet, plan to build it first and capture a
     baseline on the unchanged state.
   - For a design choice that cannot be undone, invoke `codebase-design` to compare materially
     different alternatives, through its `DESIGN-IT-TWICE.md`. Skip that for mechanical work and
     for a design already settled. Start a council only when a person asks for one.
   - Decide what runs in parallel: only across seams in the work, and never more workers than you
     can check. Give each parallel worker its own worktree or branch, stricter than `delegation`,
     which also allows a shared checkout.
   - Write the design down in a file a person can open: at the path the request names, or else a
     gitignored scratch path under `scratchpad/`. That file, the units in order with their checks,
     is what the person reviews, and the reply names it.
   - Add the designed steps to the todo list as concrete items after the Run entry (the loop) and
     before Hand back (the audit entry). Each runs under step 5.
4. **Trail.** Once the design is written, before the first unit, invoke `decision-trail`. Add each
   row as its decision lands, not in a batch at the end. This one whole call stays open through
   step 6, which runs its audit and review.
5. **Run**, one designed unit at a time, in the designed order.
   - If the framing estimates over an hour, stop once to check with the person, carrying on with
     independent work meanwhile, unless the request says to run without stopping. That stop comes
     before the first unit.
   - State the unit's hypothesis: what it should change in the predicate.
   - Make the smallest change the evidence justifies and check the predicate on it.
   - Keep a change that moved the predicate forward and revert one that did not, undoing only as
     `AGENTS.md`'s Safety section allows.
   - Each unit ends in a checked state, and the next starts only when it passes
     (`principle-sequence-verifiable-units`).
   - When a check passes more easily than the change warrants, confirm it can fail before counting
     it.
   - A unit may go to a worker through `delegation`. Give each delegated unit a judge: a check that
     can fail, or a critic through `review`. With no second agent available, the coordinator judges
     it and says so.
   - A pass won by weakening or routing around its check does not count. Undo only the edits you
     can attribute to that and have authority to undo, keep or report the rest, harden its brief
     and retry within the retry limit `delegation` sets; once that is spent, take its existing
     exit.
   - If a gate itself is wrong, fix it in its own change, within your authority, or report it;
     never route around it or loosen it inside the work it blocks.
   - Report each exit check as verified, not verified or inconclusive; inconclusive does not close
     the work.
   - Hide no negative: log and report every reverted unit, failed check, check that could not run
     and dropped unit.

   Go to step 6 when the units are done, when a blocker, an inconclusive check or a dropped unit
   leaves the predicate out of reach, or when the person says stop.
6. **Hand back**, on every exit, in this order.
   - When the units are done, check the whole against the step-2 predicate on the real product,
     not only the checks the run built, and log its result or the blocker it finds. A result that
     needs more work goes back to step 5 only when an authorized next unit can fix it and the
     person has not said stop; otherwise it is a Stopped exit.
   - On a Stopped exit, log the predicate as not verified or inconclusive, with why the final check
     did not run or pass and what remains, without starting new work to produce that row.
   - Then, once the trail is open, its audit and review, as `decision-trail` says.
   - Then the reply.

## Reply

- **Finished:** the final check against the predicate: its command and output, or the artifact
  it inspected.
- **Stopped:** blocked, inconclusive, a dropped unit or the person said stop: what stopped it and
  how to continue.
- **Not started:** no falsifiable predicate, or the framing could not be stated: why, and what is
  needed.

Every reply that got past Design gives the design's path, the rigor level and why, the trail's
path, what is verified against the predicate (verified, not verified or inconclusive), each
negative, and what is still open. After the trail opened, it ends with the trail's Attention
section, verbatim.
