---
trigger: A measured or reported slowness or resource cost to fix once against a target, with no settled plan to execute.
traits: [measurement-tied-fix-gate]   # new
steps:
  - id: perf-issue#1
    when: always
    calls: [{to: "skill:performance-optimization", when: this one whole call stays open through perf-issue#4; its steps 1-3 and vetting run here}]
  - id: perf-issue#2
    when: the vetted baseline misses the target
    calls: [{to: "skill:explain-code", when: the located cost's code is unfamiliar}]
  - id: perf-issue#3
    when: the vetted baseline misses the target; this is the skill's step 4, one candidate at a time
    actions: [{trait: implement-against-sketch}]   # when perf-issue#3 sketched
    calls: [{to: "skill:codebase-design", when: the change crosses a function boundary}, {to: "skill:delegation", when: the router's delegation rule sends the code-writing to a subagent; one brief per factor}, {to: "skill:review", when: a sketch ran}]
  - id: perf-issue#4
    when: perf-issue#3 attempted a change to code, configuration or runtime settings; this is the skill's step 5, and a candidate that misses returns to perf-issue#3
    actions: [{trait: paired-artifact-diff}]   # new
    calls: [{to: "skill:delegation", when: parsing the artifacts would flood this session's context}]
  - id: perf-issue#5
    when: every exit
    actions: [{trait: build-closeout}]
  - id: perf-issue#6
    when: finished, with a comparison past noise on the matching surface, after perf-issue#5
    actions: [{trait: measurement-in-commit-body}]   # new
    calls: [{to: "skill:land"}]
---

# Perf issue

For a measured or reported slowness or resource cost to fix once against a target,
with no settled plan. A failure or a regression whose cause is unknown is the bug-fix
playbook, and repeated climbing of one metric is the hillclimb playbook.

**The gate:** every fix ties to a measurement, and you own the number whoever writes
the code. A change with no comparison behind it is not a fix.

1. **Baseline.** Invoke `performance-optimization`. This one whole call stays open
   through step 4, so nothing of its core is skipped; its steps 1-3 and its vetting run
   here. When the target is already met or the claim does not reproduce, go to step 5.
2. **Understand.** When the located cost's code is unfamiliar, invoke `explain-code`.
3. **Change.** This is the skill's step 4: one candidate at a time, in its order, until
   its stop condition holds, which with no caller's condition is its default.
   `principle-sequence-verifiable-units` applies. When the change crosses a function
   boundary, first invoke `codebase-design` for a sketch, then build against that sketch
   as the contract: surface any departure, and revise the sketch first when the code
   must diverge. By the router's delegation rule, hand the code-writing over through
   `delegation`, one brief per factor. When a sketch ran, invoke `review` on the result.
   When no candidate is left, or a sketch or delegate cannot go on, go to step 5.
4. **Compare.** This is the skill's step 5, and it runs after any attempted change to
   code, configuration or runtime settings. Keep the baseline's and the candidate's
   artifacts from the matching surface and diff them; when parsing them would flood this
   session's context, hand the parse over through `delegation`. A candidate that misses
   the target is removed by the skill's own rule and returns to step 3. A comparison on
   another surface, or an unavailable or inconclusive one, is no pass: go to step 5 with
   no finished claim. The skill's attempt record and any regression guard finish before
   its call closes.
5. **Close out**, on every exit. Remove temporary scaffolding, name what is unfinished
   in the tree and list the open decisions.
6. **Land.** Only when finished, with a comparison past noise on the matching surface,
   after step 5: hand the measured number to `land` for the commit body and invoke it.
   No stopped, inconclusive or unavailable path lands.

## Reply

- **Finished:** baseline, post-fix number, delta, verdict, run count, spread, limiter,
  artifact paths, and `land`'s commits or plan, or its refusal and the gap it named.
- **Stopped at step 1:** the target was already met, or the claim did not reproduce,
  with the vetted number.
- **Stopped at step 3:** the sketch or diff state, what was tried and what is needed.
- **Inconclusive or unavailable:** the numbers, which gap made it so and what stays in
  the tree.

Every reply also says what the closeout removed and what it left unfinished. When
sustained work is wanted, the reply names it as the next request, which goes back
through the router.
