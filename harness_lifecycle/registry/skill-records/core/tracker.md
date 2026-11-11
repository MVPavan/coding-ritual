---
skill: tracker
domain: core
stage: X
substage: Coordination
secondary: [Decomposition, Continuity]
family: handoff
aliases: []
status: active
---
# tracker

Use to put Beads structure on approved work: seed or extend a workstream's phase epics and stages, record an approved plan (one-phase work, or units that will span sessions) or an approved decision map and its tickets, seed flat operational work from a charter, find or close a phase's epic, or render the tracking files. How a bd command, field or gate works is beads; choosing a spec's phases is to-roadmap; writing the plan is to-plan.

**Boundary:** Puts approved work structure on Beads: seeds or extends a workstream's phase epics and stages, records an approved plan, seeds flat operational work from a charter, records a wayfinder map, finds and closes a phase's epic and renders the tracking files; how bd works is beads, choosing a spec's phases is to-roadmap, writing the plan is to-plan, and running the work is implement.

<!-- registry:generated traits -->
- `phase-epic-contract`: Shape a phase epic to the status-renderer contract — a bracketed phase-id title, the roadmap as spec_id, the governing spec path as design, and acceptance matching the roadmap's verify rows.
- `phase-epic-lookup`: Find a phase's single epic by its roadmap anchor and bracketed phase-id title, treating zero or several matches as a tracking defect and never re-seeding silently.
- `workstream-layout`: Lay out a workstream as a charter, a roadmap that anchors its phase epics, a folder for just-in-time plans and a generated tracking folder, joined to the tracker by a bracketed phase-id title prefix.
- `beads-native-tracking`: Seed epics and stages and render tracking natively in the tracker, keeping the roadmap anchor on the epics and the stage mapping that execution closes against, and writing nothing before its matching approval. (The roadmap anchor is the --spec-id and the governing spec is --design; the renderer derives the workstream from the anchor, so a plan path never goes in --design.)
- `workstream-extension`: Extend a seeded workstream by seeding only its newly appended phases on the same roadmap anchor, allowing a different governing spec, and adding epic-to-epic edges only where a new phase genuinely depends on an old one.
- `dependency-edges`: Encode real blocking edges in the tracker and let the ready frontier drive execution rather than listing order.
- `real-id-wiring`: Wire cross-references and dependencies with real identifiers, never placeholders. (Creates every bead first, then wires edges and binds a plan's proposed stage names by the returned IDs.)
- `one-phase-plan-tracking`: Record an approved one-phase plan as one epic anchored on its spec with stage children carrying the plan's acceptance, and bind the plan's proposed stage names to the returned IDs before execution.
- `flat-operational-tracking`: Track phaseless operational work as one epic anchored on its charter with plain task children, without a roadmap.
- `close-gate`: Close a phase only when it has at least one stage, every stage is closed, and its roadmap exit criterion has run with evidence recorded. (Also closes a one-phase epic, whose exit evidence is the epic's acceptance rather than a roadmap exit criterion.)
- `workstream-render`: Regenerate the workstream status, ideas and backlog boards from the tracker through the render script, never hand-editing them.
- `session-spanning-unit-beads`: After a plan is approved, when its units will span sessions, give each unit a child bead under the work it belongs to, with acceptance from the unit's own evidence and edges from its dependencies by returned IDs, recording each ID beside its unit in the plan and reusing a bead that already is the unit.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/to-tickets#dependency-edges** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#publish-to-tracker** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#real-id-wiring** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/to-tickets#sub-issue-linkage** `skills/engineering/to-tickets/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#real-id-wiring** `skills/engineering/wayfinder/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-tracker:020): Owner ruling N, R2/R3 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 27 section 5 T1b with critic-27d R1/R2 applied. Unit beads branch: after plan…
- `2026-11-11` **update** (2026-11-11-tracker:019): critic-28d F2 (scratchpad/mvp-stack/critic-28d.md), coordinator fix: a title opening with '[' is reserved for a workstream phase epic; tracker gives other epic…
- `2026-11-11` **update** (2026-11-11-tracker:017): critic-28b (scratchpad/mvp-stack/critic-28b.md), coordinator-accepted, plan 27 T1a. F1: create recipes use --silent, which prints the new ID (-q prints nothing…
- `2026-11-11` **adopt** (2026-11-11-tracker:007): Owner ruling N3 (2026-11-11), plan 27 section 4a: wayfinder keeps its questions, map content, ticket meaning and resolution, and records its approved map, tick…
- `2026-11-11` **adopt** (2026-11-11-tracker:006): Owner ruling N3 (2026-11-11), with M2: the tracker skill puts our work structure on Beads, and to-roadmap, to-plan, implement, wayfinder and triage call it; th…
- `2026-11-11` **adopt** (2026-11-11-tracker:005): Owner ruling N3 (2026-11-11), with M2: the tracker skill puts our work structure on Beads, and to-roadmap, to-plan, implement, wayfinder and triage call it; th…
- `2026-11-11` **adopt** (2026-11-11-tracker:004): Owner ruling N3 (2026-11-11), with M2: the tracker skill puts our work structure on Beads, and to-roadmap, to-plan, implement, wayfinder and triage call it; th…
- `2026-11-11` **adopt** (2026-11-11-tracker:003): Owner ruling N3 (2026-11-11), with M2: the tracker skill puts our work structure on Beads, and to-roadmap, to-plan, implement, wayfinder and triage call it; th…
- `2026-11-11` **add** (2026-11-11-tracker:001): Owner rulings M2 (2026-11-10), N2 and N3 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 27 T1a. New skill: our work structure on Bead…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `beads-native-tracking`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#publish-to-tracker` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/to-tickets#sub-issue-linkage` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `dependency-edges`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#dependency-edges` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `real-id-wiring`:
  - `mattpocock_skills:skill:skills/engineering/to-tickets#real-id-wiring` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/wayfinder#real-id-wiring` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
