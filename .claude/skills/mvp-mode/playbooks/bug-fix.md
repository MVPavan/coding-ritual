---
trigger: A reported defect, failing check or flaky test to diagnose and fix with proof.
traits: [confirmed-cause-gate, stated-unattended-gate, unattended-not-started]   # the first new; variant of owning-fix without the owning layer, which AGENTS.md holds
steps:
  - id: bug-fix#1
    when: a deterministic failing command, run as reported, shows the failure and its output points at the cause; never a flaky failure, nor a cause found by reading code or rerunning in a loop
    actions: [{trait: obvious-cause-skip}]   # new
  - id: bug-fix#2
    when: bug-fix#1 did not skip it
    actions: [{trait: long-hunt-test}, {trait: bounded-background-wait}]
    calls: [{to: "skill:how", when: the failing subsystem is unfamiliar}, {to: "skill:why", when: the failure may be a regression}, {to: "skill:systematic-debugging"}]
  - id: bug-fix#3
    when: the cause is confirmed
    actions: [{trait: existing-check-as-proof}, {trait: report-missing-proof}, {trait: missing-seam-finding}, {trait: scoped-instance-fix}, {trait: implement-against-sketch}]   # the first when step 1's failing check already fails for the reported reason; the second and third only when no regression check is feasible, and the third only when no seam can hold one; the fourth always; the fifth when the fix was sketched
    calls: [{to: "skill:codebase-design", when: the fix crosses a function boundary}, {to: "skill:tdd", when: step 1's failing check does not already fail for the reported reason and a durable regression check is feasible}]
    loads: [{path: bug-fix/timing-flakes.md, when: the cause is a timing flake}]
  - id: bug-fix#4
    when: bug-fix#3 changed code
    actions: [{trait: rerun-original-repro}]   # new; variant of regression-check, the rerun alone
  - id: bug-fix#5
    when: around bug-fix#3 and bug-fix#4
    actions: [{trait: attempt-log}, {trait: revert-ineffective-experiments}, {trait: two-failure-stop}]
  - id: bug-fix#6
    when: the confirmed defect reveals another boundary problem
    actions: [{trait: defense-in-depth-hardening}]
    loads: [{path: bug-fix/hardening.md}]
  - id: bug-fix#7
    when: every exit
    actions: [{trait: closeout}, {trait: preserve-reproducers}, {trait: always-on-signal}]   # the last only when finding the cause took a deep investigation
  - id: bug-fix#8
    when: the Fixed exit, after bug-fix#7
    calls: [{to: "skill:land"}]
---

# Bug fix

For a reported defect, a failing check or a flaky test that should end
fixed. A question about a failure's cause with no fix wanted is a call to
`systematic-debugging` alone, not this playbook.

**The gate:** production code changes only for a confirmed cause. A change
that merely hides the symptom (a retry, a longer timeout, a skipped test) is
not a fix.

A run is unattended only when the request's own words say so: overnight, while I'm away, off to bed, unattended, come back by yourself, or the like. Otherwise it is attended, whatever its length.
A stated unattended request does not start: reply Not started, unattended.

1. **Obvious cause.** When a deterministic failing command, run as
   reported, shows the failure and its output points at the cause, that
   cause is confirmed: skip step 2 and go to step 3. A flaky or intermittent
   failure never qualifies, and neither does a cause found by reading code
   or rerunning in a loop.
2. **Diagnose.** When the failing subsystem is unfamiliar, first invoke `how`; when
   the failure may be a regression, first invoke `why`. Invoke `systematic-debugging` and tell it
   this playbook's closeout removes its instrumentation. Only a **confirmed**
   diagnosis goes on to step 3. On **provisional** or **unresolved**, change no
   production code and go to step 7. A mitigation for an unresolved cause ships
   only on the user's decision, never as the fix.
   A hunt is long only when its next evidence cannot arrive within one foreground command: the reproduction or capture runs longer than one may, or fires on its own schedule. A stubborn hunt with something to run now is not long: keep running.
   Waiting on a command: run it in the background with a finite lifetime and take the platform's completion notice, or wait in the foreground. If the runtime gives neither for what must be waited on, take the stopped-waiting exit.
3. **Fix with proof.** When the fix crosses a function boundary, first invoke
   `codebase-design` for a sketch, then build against that sketch as the contract:
   surface any departure, and revise the sketch first when the code must diverge.
   When the failing check from step 1 already fails for
   the reported reason, it is the regression check: fix the cause and show
   it passing. Otherwise, when a durable regression check is feasible,
   invoke the `tdd` skill in test-first mode rather than
   running the cycle by hand: the check fails for the reported reason before
   the fix and passes after it. Otherwise fix the confirmed cause and report
   the missing proof; when no seam can hold a regression check, record the
   missing seam as a finding. For a timing flake, read `bug-fix/timing-flakes.md`
   first. Search for other instances of the confirmed fault: fix those
   inside the task's scope and report the rest.
4. **Rerun.** Run the original scenario as reported, not only the minimised
   reproduction, and the repository checks the change touches. An
   inconclusive rerun is not a pass: report it as inconclusive. When the
   original scenario cannot be run, report it as unavailable.
   When the project has a verify skill for the reported surface, reproduce and rerun through it; with none, suggest `/create-verification-skill`.
5. **Attempts.** Around steps 3 and 4, record each attempt as hypothesis,
   change and result, and remove a failed attempt's own changes before the
   next. When a failure puts the cause in doubt, return to step 2 with the
   log. After two failed fixes, stop and go to step 7 with the log.
6. **Harden.** Only when the confirmed defect reveals another boundary
   problem: read `bug-fix/hardening.md` and harden the bug class just fixed.
   Record hardening beyond that class as follow-up.
7. **Close out**, on every exit, fixed or not. Remove the temporary
   instrumentation added (search its tag), keep reproducers and user
   artifacts, and record the cause or the status reached, the proving check
   if there is one, and the remaining limits. When finding the cause took a
   deep investigation, propose the cheap always-on signal that would have
   shown it at first look; do not add it.
8. **Land.** Only on the Fixed exit, after step 7: invoke `land`. No stopped or
   unverified path lands, and neither does `Changed, verification incomplete`.

## Reply

- **Fixed**, only when the original scenario passed its rerun: what was
  broken, the cause and what confirmed it, the fix, the proving check with
  its failing and passing output (or the missing proof), the rerun's result,
  limits and follow-ups, and `land`'s commits or plan, or its refusal and the
  gap it named.
- **Changed, verification incomplete**, when the rerun was inconclusive or
  the original scenario unavailable: the cause, the change, the proof
  available, which scenario could not be verified and why, and the evidence
  still needed to call it fixed.
- **Stopped at step 2, provisional, which is also the stopped-waiting exit:** the reproduction if
  there is one, the analysis, the remaining hypotheses, the evidence requested, any proposed
  fix labelled unproven, that no production code changed, and what is outstanding, where its
  evidence will appear, and that nothing will resume by itself.
- **Stopped at step 2, unresolved:** the finding with its investigation, and
  any mitigation as an option for the user, not applied.
- **Stopped at step 5:** the attempt log, the current explanation and what
  is needed to continue.
- **Not started, unattended:** why, an offer of an attended run, and an offer of an Autonomous run
  asked for by name, if the person can state a checkable condition such as the test passing 50 times
  in a row; that route has no confirmed-cause gate.

Every reply also says what the closeout removed and what it kept.
