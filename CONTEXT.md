# Coding Ritual

A meta-repository for building reusable agent harnesses and curating patterns from
third-party reference harnesses. This glossary is the repo's vocabulary — use these
terms in issue titles, docs, and code; avoid the listed synonyms.

## Language

### Harness anatomy

**Harness**:
The agent-facing setup of a repo — rules, skills, commands, subagents, hooks — under `.claude/` and `.codex/`.
_Avoid_: scaffolding, config, setup

**Reference harness**:
A third-party harness tracked read-only as a git submodule under `reference_harnesses/`. Inspiration to borrow from, never to copy wholesale or edit.
_Avoid_: upstream (ambiguous with git), vendor

**Project overlay**:
The repo-specific facts in `.claude/project/` and `.codex/project/`, refreshed per repo; the harness core stays identical across repos.
_Avoid_: project config

**Template**:
The generated, installable copy of the harness inside `mvp-harness/`. Always a strict subset of the root harness; built, never hand-edited.
_Avoid_: boilerplate

**Mirror**:
A bd-generated read-only projection (workstream tracking files, boards). Update beads, then re-render — never hand-edit.
_Avoid_: report, dashboard

### Work management

**Workstream**:
A named body of work with its own directory under `docs/workstreams/`, a roadmap, and bd epics.
_Avoid_: project, initiative

**Roadmap**:
The phased plan of one workstream; every phase epic points at it via `--design`.
_Avoid_: plan (that is the per-phase document), spec

**Phase**:
One roadmap unit of execution, materialised as one bd epic.
_Avoid_: milestone, sprint, iteration

**Stage**:
One deliverable inside a phase; one flat bd task child of the phase epic.
_Avoid_: step (an in-turn action), subtask

**Plan**:
The per-phase implementation document written for deep phases (`plans/<phase>.md`).
_Avoid_: roadmap, design doc

**Idea doc**:
The output of idea-refine, at `docs/ideas/<topic>.md` — a decision to pursue one direction, its bets named. Not yet a commitment to build; may be parked or dropped without shame.
_Avoid_: proposal, concept doc

**Spec**:
The approved output of brainstorming, at `docs/specs/YYYY-MM-DD-<topic>.md` — the commitment to build: behaviour, acceptance, testing, scope. What planning and phase preparation consume; every phase epic points at it via `--spec-id`.
_Avoid_: requirements doc, brainstorm doc, design doc

**Bead**:
One durable work item in bd. In-turn steps are not beads.
_Avoid_: ticket, todo

**Ready-for-agent**:
Specified enough for autonomous execution — the intake gate in `.beads/beads.md`. Distinct from `bd ready`, which means only unblocked.
_Avoid_: ready (unqualified)

### Curation

**Bucket**:
One of the 14 capability categories used to compare skills across harnesses.
_Avoid_: category, group

**Capability family**:
The redundancy axis — skills across harnesses claiming the same job.
_Avoid_: cluster

**Ledger**:
The current curation ruling per reference capability (adopt / reject / defer) in `harness_lifecycle/ledger.json`. Mutable — one entry per capability, no history.
_Avoid_: casebook, changelog

**Casebook**:
The append-only history of curation rulings per bucket — what changed and why the ledger says what it says.
_Avoid_: ledger

**Adoption**:
Two senses — always qualify. *Capability adoption*: taking a reference-harness pattern into this harness, recorded in the ledger. *Repo adoption*: installing the template into a target repo via `/adopt`.
