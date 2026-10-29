---
skill: triage
domain: core
stage: Intake
substage: Triage
secondary: []
family: issue-state-management
aliases: []
status: active
---
# triage

## Capability

Evaluate untriaged beads and decide each one — agent-ready under a parent, owner's work, questions for the owner, deferred, or a wontfix close. Use to review what needs attention or to triage a specific bead.

<!-- registry:generated traits -->
- `triage-routing`: Route each triaged item to one outcome expressed in the tracker's native fields (admit with acceptance, hand to a human task, defer, reject, or mark duplicate) with no separate intake labels.
- `attention-buckets`: Present the items needing triage attention as named buckets, oldest first. (Four buckets (untriaged, ideas, waiting on the owner, missing acceptance) with counts and one-line summaries.)
- `triage-decision`: Decide and apply each triage outcome within existing authority rather than deferring every call to the owner.
- `triage-resume-notes`: Resume triage from the notes of earlier passes, never re-asking a question already answered.
- `redundancy-check`: Search the codebase by domain concept for an existing implementation and report where you looked before deciding.
- `prior-rejection-check`: Check earlier rejections for one resembling the request and surface any match before deciding. (Searches closed beads for earlier wontfix closes.)
- `claim-verification`: Verify a reported claim before acting on it, reproducing a bug or recording exactly why it could not be reproduced. (An unreproduced bug gets questions for the owner, never an automatic close.)
- `agent-ready-gate`: Make a bead agent-executable only when acceptance criteria, current and desired behaviour, and out-of-scope notes all hold.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/triage** `reference_harnesses/mattpocock_skills/skills/engineering/triage/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/engineering/triage** `skills/engineering/triage/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-12` **adopt** (2026-10-14-migration:105): Adapted, not copied: state machine remapped onto beads natives (category=bd type; needs-info/human labels + bd human; wontfix=close-reason, replacing .out-of-s…
- `2026-08-11` **adopt** (2026-10-14-migration:031) *(superseded)*: The only inbound-work state machine, with concept-level redundancy checks and a prior-rejection knowledge base so the same proposal is not re-litigated.
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
None yet.
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
