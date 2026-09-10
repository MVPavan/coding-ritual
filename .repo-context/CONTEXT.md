# Project Vocabulary

Use these terms for the domain concepts below. Ordinary words remain valid
outside these meanings; this glossary does not prescribe a skill or workflow.

## Harness anatomy

**Harness**: The agent-facing setup: entry instructions, shared repository
context, skills, agent definitions, hooks, and runtime integrations.

**Reference harness**: A third-party harness tracked under
`reference_harnesses/` as a source of patterns.

**Repository context (project overlay)**: Repo-specific facts and guidance in
`.repo-context/`, shared across agent runtimes.

**Template**: The installable distribution of the reusable harness in
`mvp-harness/`. Distribution status is separate from the root harness;
see `docs/usage/mvp-plugin.md`.

**Mirror**: A generated projection of Beads state, such as a workstream board
or tracking file. Beads owns the underlying state.

## Work management

**Workstream**: A named body of work with a roadmap and Beads epics. Its documents
conventionally live under `docs/workstreams/`.

**Roadmap**: The phased plan for a workstream.

**Phase**: One roadmap unit of execution, represented by a Beads epic.

**Stage**: One deliverable within a phase, represented by a child task.

**Plan**: The detailed implementation document for a phase when needed,
usually under its `plans/` directory.

**Idea doc**: A proposed direction with its bets and open questions, usually in
`docs/ideas/`. It is not yet a commitment to build.

**Spec**: The agreed behavior, scope, acceptance criteria, and verification
requirements that planning and execution consume, usually in `docs/specs/`.

**Bead**: One durable work item in Beads (`bd`), distinct from an in-turn step.

**Ready-for-agent**: Specified enough for autonomous execution under
`.beads/beads.md`. Distinct from `bd ready`, which means unblocked.

## Workflow interpreter

**Workflow instance**: One execution of a pinned workflow, with its own durable
state and execution history.

**Pinned graph**: The resolved workflow definition frozen for an instance and
identified by its canonical content hash.

**Activation**: One recorded execution attempt of a task node within an instance.

**Gate**: A workflow pause awaiting an authenticated decision. In v1 this is an
interpreter-managed Bead, distinct from native `bd gate` machinery.

**Carrier**: A typed record carrying interpreter state or a request across
storage or component boundaries.

The authoritative interpreter semantics are in
`docs/specs/workflow-interpreter.md`; persisted carriers are defined in
`workflow_interpreter/bdio/wire.py`.

## Reference curation

**Bucket**: A capability category used to compare skills across harnesses.

**Capability family**: Skills across harnesses claiming the same job, compared
for overlap and redundancy.

**Ledger**: The current adopt/reject/defer ruling per reference capability in
`harness_lifecycle/ledger.json`.

**Casebook**: The append-only history explaining curation rulings by bucket.

**Adoption**: Qualify the two meanings: *capability adoption* brings a reference
pattern into this harness; *repo adoption* installs the distributed harness into
a target repository.
