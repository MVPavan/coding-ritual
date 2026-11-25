---
trigger: An artifact captured earlier (trace, profile, heap dump, core) to explain, with no fix wanted.
traits: [fixed-artifact-gate, no-fix-handback]   # new; variant of diagnosis-only, with no instrumentation allowed
steps:
  - id: trace-forensics#1
    when: always
    actions: [{trait: artifact-format-load}]   # new
    calls: [{to: "skill:delegation", when: parsing the artifact would flood this session's context}]
  - id: trace-forensics#2
    when: the artifact is not already in a form that can be queried
    actions: [{trait: queryable-dump-first}]   # new
  - id: trace-forensics#3
    when: always
    actions: [{trait: narrow-by-artifact-shape}]   # new
  - id: trace-forensics#4
    when: a cause has been narrowed to a frame, object or thread
    actions: [{trait: source-attribution-or-gap}]   # new
  - id: trace-forensics#5
    when: a cause has been narrowed to a frame, object or thread
    actions: [{trait: paired-capture-confirmation}]   # new; a paired capture confirms, otherwise the finding is labelled a hypothesis
  - id: trace-forensics#6
    when: every exit
    actions: [{trait: forensics-closeout}]   # new
---

# Trace forensics

For an artifact captured earlier, such as a trace, profile, heap dump or core,
to explain with no fix wanted. A request that also wants the fault fixed or the
slowness removed starts with the router, not here. Evidence still to capture
from a live process is not this playbook either.

**The gates:** the artifact is a fixed dataset, so read and query it; never
re-run the scenario to get a different one, and never change the artifact. The
deliverable is a diagnosis; change no code, and add no instrumentation.

1. **Load.** Identify the format and open it with a tool made for it. When
   parsing it would flood this session's context, hand the parse to a subagent
   through `delegation` and keep only its reduced finding here. When no tool can
   read it, go to step 6.
2. **Make it queryable.** Before reading the data, dump it to a form you can
   query, with one row per sample, frame or node. Python's standard `sqlite3`
   needs nothing installed. Put the dump in temporary space, never beside the
   artifact. Skip this when the artifact can already be queried.
3. **Narrow.** Let the artifact's shape set the query: the frames holding the
   most time and the call tree down to the hot path; the retainer chain from a
   leaked object to a root; the stuck thread and what it waits on. When nothing
   narrows, go to step 6 and report how far the reading got.
4. **Attribute.** Map the finding to a file, symbol and line through the
   artifact's own symbols. A frame with no source is not yet a diagnosis:
   resolve its symbols, or say plainly that the artifact does not carry them.
5. **Confirm.** With a paired capture, diff before against after, and the diff
   confirms or refutes the finding. Without one, label the finding the strongest
   hypothesis this artifact supports, not a confirmed cause.
6. **Close out**, on every exit. Leave the artifact unchanged, name the dump and
   any query scripts you kept, and delete the rest.

## Reply

A cited diagnosis handed back; no fix.

- **Diagnosed:** the artifact and its format, the reduced finding, the source
  location, the artifact's path, whether a paired capture confirmed it or it
  stands as the strongest hypothesis, and the queries that produced the finding.
- **Stopped, unreadable or unattributed:** the artifact and its format, how far
  the reading got, what is missing (a parser, symbols, a paired capture) and the
  evidence needed to continue.

When the finding is a defect or a slowness, the reply says so and names it as
the next request, which goes back through the router. This run does not start
that work.

Every reply also says which derived files the closeout kept and where.
