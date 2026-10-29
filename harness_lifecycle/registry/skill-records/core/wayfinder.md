---
skill: wayfinder
domain: core
stage: Discovery
substage: Charting
secondary: []
family: task-decomposition
aliases: []
status: active
---
# wayfinder

## Capability

Map and resolve material decision dependencies across a multi-session effort.

<!-- registry:generated traits -->
- `decision-map-epic`: Chart a large effort as one map item on the tracker whose children are decision tickets. (A Beads epic whose title starts with Map:.)
- `plan-not-do`: Keep the map to planning: each ticket resolves a decision rather than executing a build slice.
- `dependency-edges`: Encode real blocking edges in the tracker and let the ready frontier drive execution rather than listing order.
- `map-as-index`: Keep resolution detail on each ticket while the map holds only a named pointer and a gist.
- `map-body-sections`: Structure the map body as Destination, Notes, Decisions so far, Not yet specified, and Out of scope.
- `reference-by-name`: Reference tickets by name with identifiers and links so the map reads without opening every item.
- `bounded-decision-ticket`: Make each ticket one bounded question whose answer is a decision. (With a resolution criterion.)
- `coherence-sized-tickets`: Size decision tickets by decision coherence and dependencies, not an assumed context-window size.
- `label-free-typing`: Express each ticket's kind through the tracker's native item type and a title prefix, creating no labels.
- `ticket-type-set`: A fixed set of ticket kinds: research for facts, prototype for fidelity, grilling for a live interview, and task for prerequisite work that unblocks a decision. (Task work must be authorized.)
- `claim-before-work`: Choose the requested or a ready unclaimed child and claim it before working on it.
- `destination-first`: Name the destination first, since it fixes the scope and shapes every ticket.
- `question-graduation`: Ticket a question once it is sharp enough to state, even while blocked, and hold not-yet-specifiable work aside until earlier answers make it expressible.
- `real-id-wiring`: Wire cross-references and dependencies with real identifiers, never placeholders. (Creates the items first, then wires them.)
- `record-resolution`: On resolving a ticket, record the answer on it, close it, and add a pointer to the map's decisions so far. (Updates invalidated dependencies without deleting history.)
- `out-of-scope-close`: Close an out-of-scope ticket with an explicit exclusion reason rather than a claim of delivery.
- `human-decision-gate`: Stop at a required human decision and prepare concrete options before requesting the final gate.
- `multi-ticket-sessions`: Continue through additional authorized ready tickets with no one-ticket-per-session limit, parallel work needing disjoint ownership.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/wayfinder** `reference_harnesses/mattpocock_skills/skills/engineering/wayfinder/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/engineering/wayfinder** `skills/engineering/wayfinder/SKILL.md`
- **mattpocock_skills:skill:skills/engineering/wizard** `skills/engineering/wizard/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/in-progress/loop-me** `skills/in-progress/loop-me/SKILL.md` @ 84fdeff
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:142): Adopted-in-part: push-right and decision-summary (renamed from 'brief' — documented task-brief collision) into wayfinder, scoped to AFK-internal gates with Pro…
- `2026-08-14` **adopt** (2026-10-14-migration:140): Adopted-in-part: verify-what-you-must-not-run discipline (static trace + CI secret name-matching) into wayfinder's Task ticket type. The 204-line template.sh m…
- `2026-08-12` **adopt** (2026-10-14-migration:106): Copied verbatim (SKILL.md + agents/, ships user-invoked via disable-model-invocation). Adopted as-is per user decision 2026-08-12; local customization (beads-n…
- `2026-08-11` **adopt** (2026-10-14-migration:032) *(superseded)*: The only planner for work larger than one context window under genuine uncertainty: fog-of-war decision tickets resolved one at a time until the route is clear…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/interaction-utilities](../../../archive/skill-comparisons/interaction-utilities/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
No adopted traits recorded.
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
