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

**Agent-ready**: An open bead with acceptance criteria, which an agent may take
(the `beads` skill, `references/usage.md` §10). Distinct from `bd ready`, which
means unblocked.

## Workflow interpreter

**Contractor**: Takes one tracker task through a landed commit and closure;
CLI command `contract`. Formerly the phase bridge (`bridge/`, `PhaseBridge*`).

**Foreman**: Makes one decision per tick; does not execute the work. Name unchanged.

**Inspector**: Contains and watches an activation, records its exit, and grades
its claim; CLI command `inspector`. Formerly supervisor (`supervisor/`, `Supervisor*`,
`supervise`).

**Crew**: The vendor CLI doing work within an activation. Formerly runner
(`Runner*`, `runner` node key).

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

**Registry**: `harness_lifecycle/registry/`: our skill records, rulings on
reference capabilities, and the ledger that holds both.

**Coordinate**: A skill's one primary home: domain · ADLC stage · sub-stage.
Replaced the 14 buckets, which survive only as frozen history.

**Capability family**: Skills across harnesses claiming the same job, compared
for overlap and redundancy.

**Ledger**: The registry's append-only JSONL record of every skill change and
every ruling on a reference capability (`registry/ledger/`). The ruling on a
subject is its latest event not superseded.

**Casebook**: The frozen 2026-08 curation record (`harness_lifecycle/archive/casebook/`);
its events were migrated into the registry ledger.

**Prompting guide**: `harness_lifecycle/prompting-guides/GUIDE.md`, the
vendor-derived rules for writing agent instructions, with its ledger. Used only
when changing this repository's skills and instructions; never shipped or
referenced by shipped files.

**Writing principles**: `.claude/skills/authoring-for-agents/references/writing-principles.md`,
the distilled excerpt of the prompting guide. The only writing guidance that
ships to other repositories.

**ADLC guide**: `harness_lifecycle/adlc/GUIDE.md`, the lifecycle stages, their
design principles, and how skills map onto them. It gives no advice on writing
skills.

**Adoption**: Qualify the two meanings: *capability adoption* brings a reference
pattern into this harness; *repo adoption* installs the distributed harness into
a target repository.
