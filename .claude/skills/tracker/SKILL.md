---
name: tracker
description: "Use to put Beads structure on approved work: seed or extend a workstream's phase epics and stages, record an approved plan (one-phase work, or units that will span sessions) or an approved decision map and its tickets, seed flat operational work from a charter, find or close a phase's epic, or render the tracking files. How a bd command, field or gate works is beads; choosing a spec's phases is to-roadmap; writing the plan is to-plan."
---

# Tracker

Record approved work structure in Beads so its ready frontier drives execution.
The callers decide the structure: `to-roadmap` the phases and stages, `to-plan` the
plan, `wayfinder` the decision map; `implement` asks for lookup, rendering and the
close gate. bd itself (types, fields, waits, claims) is the `beads` skill.

## Gate

- No Beads write before the structure or plan it records is approved; recorded
  approval covering it counts, and an authorized `wayfinder` run covers its own map.
- `--actor "<coding-agent>:<unique-id>"` on every write, the same all session.
- Search first (`bd search`, `bd list --spec <prefix>`) and reuse existing records;
  never seed a duplicate.
- Create with `--silent`, which prints only the new ID (`-q` prints nothing):
  `id=$(bd create … --silent) || exit; test -n "$id" || exit 1` before any write
  that uses it.
- A title opening with `[` is reserved for a workstream phase epic (`[<phase-id>] <name>`);
  give every other epic a plain opening word (`CLI: Reader`, not `[CLI] Reader`), and
  retitle a reused one that opens with `[` (`bd update <id> --title …`). The renderer
  reads a bracketed epic as a phase.
- Wire edges only after every bead exists, by the IDs `bd create` returned, and only
  where one genuinely needs another; never chain by listing order.

## Branches

| Condition | Do |
|---|---|
| Workstream: an approved roadmap to seed, or new phases appended to one | Read `references/workstreams.md`, then seed or extend |
| One-phase plan: an approved plan for work of one phase, with no roadmap | One-phase plan, below |
| Plan record: an approved standalone plan, a task | Plan record, below |
| Unit beads: an approved plan whose units will span sessions | Unit beads, below |
| Decision map: an approved map and its tickets, supplied or handed over by `wayfinder` | Decision map, below |
| Flat operational work: a charter with recurring or plain tasks, no phases | Flat work, below |
| A phase's epic to find, close or render | Phase epics, below |

**One-phase plan.** Create or reuse one epic: `--spec-id` the governing spec, its
acceptance the spec's success criteria, a `plan: <path>` note. Create one stage
child per `Stage: proposed <name>` in the plan, with acceptance from the plan's
covering tasks, then wire the real edges. **Bind** each `Stage: proposed <name>` in
the plan to its returned `<epic>.N` before `implement` starts; on a Skeleton plan,
rerun `.claude/skills/to-plan/scripts/check_plan.py <plan>` until it exits 0. The
binding records the approved structure; it changes no scope. The consumer is task
scope, not the phase loop: no roadmap, no workstream directory.

**Plan record.** For a standalone plan with no bead yet:
`bd create "<title>" -t task --description "<why and what it changes>" --acceptance "<the plan's goal, checkably>" --notes "plan: <plan-path>" --actor … --silent`,
capturing the ID as the Gate says.
Dotted children only for genuinely independent units within the ask, or for units
that will span sessions (Unit beads). A plan's path goes in notes
(`bd note <id> "plan: <path>"` on an existing bead), never in `--design` or `--spec-id`.

**Unit beads.** After the plan is approved, when its units will span sessions,
give each unit one child task: acceptance from its Evidence boxes and their pass
conditions (Skeleton) or its `Verification:` (Elaborate), edges from its
`Dependencies:` by the returned IDs, and the ID beside its task in the plan
(`### Task N: <name> (bead <id>)`; rerun `check_plan.py` on a Skeleton plan). A stage
that already is the unit is reused, never duplicated. The units hang under:

- a standalone plan: its plan bead;
- a one-phase epic: the stage; a stage that one plan task maps to is itself the
  unit (epic, stage, unit uses bd's one subtask level);
- a spec: the ticket;
- a workstream or phase: the stage, which `implement` then runs itself, never
  through the contractor.

**Decision map.** The approved map, supplied or handed over by a `wayfinder` run,
gives the map body, each ticket's question, type and title, and the genuine
prerequisites. Create one `-t epic` titled `Map: …` with the tickets as its
children, then wire the prerequisite edges by returned ID. Later graduated tickets
join the same way. Return every ID to the caller (`wayfinder` when it handed over).

**Flat work.** One epic with `--spec-id docs/workstreams/<name>/README.md` (the
charter, layout in `references/workstreams.md`) and plain task children, each with
acceptance; no phases, no roadmap.

## Phase epics

- **Contract.** A workstream's phase epic is titled `[<phase-id>] <phase name>`; its
  `spec_id` is the roadmap `docs/workstreams/<name>/roadmap.md` (the anchor that
  names the workstream), its `design` the governing spec's path, and each stage's
  acceptance matches the roadmap's Verify cell.
- **Find.** `bd list -t epic --all --spec docs/workstreams/<name>/ --json`: exactly
  one title starts with `[<phase-id>]`; the anchor is authoritative. Zero or several
  matches is a tracking defect to report; never silently re-seed.
- **Close gate.** `bd list --parent <epic> --all --json` must show at least one
  stage and every stage closed; name the unclosed ones otherwise. The exit evidence
  must be recorded: the roadmap's `Exit (phase):` line for a phase epic, the epic's
  acceptance for a one-phase epic. If it has not run, stop and report that the
  exit is due; running it is the implement playbook's (at top level, return to
  `mvp-mode`; in a delegated task, report the route).
  Then close with the evidence as `--reason` and as a comment.
- **Render.** After any change, update Beads, then run
  `BD_RENDER=1 bash .claude/skills/tracker/scripts/bd-render-tracking.sh [<name>]`.
  It writes `docs/workstreams/{status,ideas,backlog}.md` and each workstream's
  `tracking/*.md`; never hand-edit them (a hook blocks it). The ideas board lists
  deferred spikes, the backlog board every other deferred bead. `README.md`,
  `roadmap.md` and `plans/*.md` stay hand-written. A missing renderer is a reported
  gap, never permission to write those files by hand.

## Deliverable

The tracker state created, linked or closed, reported with every ID and edge, and the
render run or its gap named. Report proposed commits; make none without authority.
