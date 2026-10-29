---
skill: beads
domain: core
stage: X
substage: Continuity
secondary: []
family: handoff
aliases: []
status: active
---
# beads

## Capability

Use for Beads (bd) work beyond the core rules injected at session start - creating epics, plans or decision beads, dependencies and gates, triage, recovery, workstream tracking, reviews, setting up or joining a Beads project, or questions about Beads policy.

<!-- registry:generated traits -->
- `bead-type-taxonomy`: Use only the six bead types (epic, feature, task, bug, spike, decision) and the single human label, never inventing others.
- `field-roles`: Give each bead field its single job — description, design, acceptance, spec_id, notes, comments and close reason — and never overload one.
- `wait-as-edge`: Record every wait as an explicit edge — a blocks dependency, a human task, or a gate — written in the needs direction so ready-work stays truthful.
- `actor-identity`: Carry one stable actor for the whole session, claiming on start and acting only on your own claims.
- `resume-line`: On pause or handoff, unclaim and append a resume line naming the approach to resume with and where the work stands.
- `session-close`: Close a session by closing finished beads with evidence, unclaiming the rest with resume lines, running the gates, refreshing the export, and reporting.
- `session-recovery`: At session start or after compaction, list in-progress beads and resume from each one's last note.
- `knowledge-in-files`: Keep durable knowledge in files, never in the tracker's remember, memories or key-value stores.
- `beads-setup`: Install the tracker, adopt it in a project, and join from a new clone with bootstrap rather than a re-init.
- `workstream-render`: Regenerate the workstream status, ideas and backlog boards from the tracker through the render script, never hand-editing them.
- `status-model`: Drive status through the model's own transitions — the custom review status, deferred as the whole backlog, and never a hand-set blocked.
- `triage-routing`: Route each triaged item to one outcome expressed in the tracker's native fields (admit with acceptance, hand to a human task, defer, reject, or mark duplicate) with no separate intake labels. (Sets a numeric priority with the outcome.)
- `durable-unit-scope`: Track one durable unit of work per bead, keeping turn checklists out, searching before creating, and filing incidental finds as discovered-from beads.
- `review-as-task`: Represent a review as its own task by an actor other than the author, which the reviewed bead depends on and sits in review status until it passes.
- `phase-epic-contract`: Shape a phase epic to the status-renderer contract — a bracketed phase-id title, the roadmap as spec_id, the governing spec path as design, and acceptance matching the roadmap's verify rows.
- `destructive-command-guard`: Never run the tracker's deleting commands, reclaiming space with a non-destructive compact instead.
- `repeated-procedures`: Capture short repeated runs as disposable wisps and fixed multi-step procedures as poured formulas, checking what the tracker actually parsed.
- `dolt-sync`: Treat the versioned database as the source of truth and the exported jsonl as a review mirror, syncing copies only with authority.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/productivity/handoff** `skills/productivity/handoff/SKILL.md` @ 84fdeff
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:147): Adopted-in-part: session close now records method with state (beads.md Session Close step 5 — which skills/approach the next session resumes with). Supersedes …
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/session-handoff](../../../archive/skill-comparisons/session-handoff/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
