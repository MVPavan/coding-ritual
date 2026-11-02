---
trigger: A symptom in a process running now (spinning, leaking, stuck) to diagnose from what it is doing, with no fix wanted.
traits: [live-diagnosis-gate]   # new; variant of diagnosis-only, no-fix-handback and fixed-artifact-gate
steps:
  - id: runtime-forensics#1
    when: always
    calls: [{to: "skill:performance-optimization", when: its diagnosis-only branch for a caller's live capture; evidence only}, {to: "skill:delegation", when: parsing the artifact would flood this session's context}]
  - id: runtime-forensics#2
    when: runtime-forensics#1 located a candidate
    calls: [{to: "skill:systematic-debugging"}]
  - id: runtime-forensics#3
    when: every exit
    actions: [{trait: live-forensics-closeout}]   # new; variant of forensics-closeout
---

# Runtime forensics

For a symptom in a process running now (spinning, leaking, stuck), diagnosed from what
it is doing, with no fix wanted. An artifact captured earlier is the trace-forensics
playbook. A request that also wants the fault fixed or the slowness removed starts with
the router, not here.

**The gate:** capture from the live process rather than theorise from source, within the
capture boundary of the skill's diagnosis-only branch. Change no code to fix it. Without
what a capture needs, go to step 3 and say so. A restart can destroy the symptom, so it
is the last resort.

1. **Capture.** Invoke `performance-optimization` on its diagnosis-only branch, as a
   caller wanting a live capture: evidence only, with no cause named.
   `principle-explain-the-number` applies to any number it reports. When parsing the
   artifact would flood this session's context, hand the parse over through `delegation`
   and keep only the reduced finding here. When nothing could be captured, go to step 3.
2. **Prove.** With a candidate from step 1, `located` or `hypothesis`, invoke
   `systematic-debugging`. Its brief gives the artifact and the reduced finding as the
   evidence it preserves, and says this playbook's closeout removes its instrumentation.
   On a live process, proof means captures or probes that tell the hypotheses apart
   (another copy of the same hot stack proves nothing), or instrumentation in a restarted
   copy, with the user's explicit yes. Its status decides the reply.
3. **Close out**, on every exit. Leave the process as found, remove any instrumentation
   by its tag and name the artifacts kept.

## Reply

A cited diagnosis handed back; no fix.

- **Confirmed:** the signal captured, the reduced finding, how the mechanism was proved,
  the source location and the artifact paths.
- **Provisional:** the same, with the remaining hypotheses and the evidence still needed.
- **Unresolved:** the finding with its investigation, as `systematic-debugging` reports it.
- **Stopped, no capture:** the surface, tool or permission missing and what is needed.

When the finding is a defect or a slowness, the reply says so and names it as the next
request, which goes back through the router. This run does not start that work.

Every reply also says what the closeout removed and which artifacts it kept.
