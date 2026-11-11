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

Map and resolve material decision dependencies across a multi-session effort.

**Boundary:** Maps and resolves the material decisions of a multi-session effort and records its map and tickets through tracker; open questions settled within one session are discovery, and a route already clear is to-plan or implement.

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
- `record-resolution`: On resolving a ticket, record the answer on it, close it, and add a pointer to the map's decisions so far. (Updates invalidated dependencies without deleting history.)
- `out-of-scope-close`: Close an out-of-scope ticket with an explicit exclusion reason rather than a claim of delivery.
- `human-decision-gate`: Stop at a required human decision and prepare concrete options before requesting the final gate.
- `multi-ticket-sessions`: Continue through additional authorized ready tickets with no one-ticket-per-session limit, parallel work needing disjoint ownership.
- `prototype-ticket-asset`: Resolve a prototype ticket by building a rough artifact and linking it from the ticket as an asset.
- `fog-hygiene`: Keep decided, ticketed and out-of-scope items out of the map's section of not-yet-specified questions.
- `low-res-map-load`: When working a map, load only its low-resolution body and open related tickets only on demand.
- `breadth-first-charting`: Chart by questioning breadth-first across the whole space to surface the open decisions and first steps before going deep on any. (Delivers sealed row 2026-10-30-mattpocock_skills-5beb35b:149: surfaces the open decisions before resolving any, where the definition charts by questioning and surfaces first steps too; T5.)
- `invalidated-ticket-reconciliation`: Update or delete the other tickets that a recorded decision invalidated. (Delivers sealed row 2026-10-30-mattpocock_skills-5beb35b:156: update or close, never delete, where the definition allows deleting; T5.)
- `prerequisite-task-human-checklist`: Do prerequisite task work alone where possible, otherwise hand the human a precise checklist.
- `prerequisite-task-result-facts`: Record on a prerequisite task the resulting facts later tickets depend on, such as URLs or where credentials live.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/wizard** `skills/engineering/wizard/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/in-progress/loop-me** `skills/in-progress/loop-me/SKILL.md` @ 84fdeff
- **mattpocock_skills:skill:skills/engineering/wayfinder#decision-map-epic** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#plan-not-do** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#reference-by-name** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#map-as-index** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#map-body-sections** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#bounded-decision-ticket** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#claim-before-work** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#dependency-edges** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#ticket-type-set** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#live-human-resolution** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#question-graduation** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#out-of-scope-close** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#real-id-wiring** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#no-triage-labels** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#type-directed-resolution** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#destination-first** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#record-resolution** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#prototype-ticket-asset** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#fog-hygiene** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#low-res-map-load** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#breadth-first-charting** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#invalidated-ticket-reconciliation** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#prerequisite-task-human-checklist** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/wayfinder#prerequisite-task-result-facts** `skills/engineering/wayfinder/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-11` **update** (2026-11-11-discovery:020): Owner ruling L1 of 2026-11-10 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 20 D5 (sections 4.5, 7.1): a `Research:` ticket calls the research sk…
- `2026-11-11` **update** (2026-11-11-tracker:009): Owner rulings M2 (2026-11-10), N2 and N3 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 27 T1a. Section 4a: the map, its tickets and …
- `2026-11-11` **update** (2026-11-10-renames-splits:160): Owner rulings M1, M4 (2026-11-10) and N1, N2 (2026-11-11) (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 24 U8r. A clear route uses to-plan or imp…
- `2026-11-09` **adopt-merged** (2026-11-09-pocock-4ae2317:168): Checkpoint at 4ae2317 for the owner's trait rulings: 1 adopt.
- `2026-11-06` **update** (2026-11-06-renames:015): Owner ruling D of 2026-11-05 (scratchpad/mvp-stack/13/owner-rulings-2026-11-05.md), plan 14a U1. A clear route goes to the units planning or implement, now nam…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:037): Completes pending 2026-10-30-mattpocock_skills-5beb35b:155: prerequisite-task-result-facts is written at .claude/skills/wayfinder/SKILL.md:31-33, in the sealed…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:036): Completes pending 2026-10-30-mattpocock_skills-5beb35b:154: prerequisite-task-human-checklist is written at .claude/skills/wayfinder/SKILL.md:30-31, in the sea…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:035): Completes pending 2026-10-30-mattpocock_skills-5beb35b:156: invalidated-ticket-reconciliation is written at .claude/skills/wayfinder/SKILL.md:51-52, in the sea…
- `2026-11-04` **adopt** (2026-11-04-pocock-pass:034): Completes pending 2026-10-30-mattpocock_skills-5beb35b:149: breadth-first-charting is written at .claude/skills/wayfinder/SKILL.md:42-44, in the sealed rewordi…
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:566) *(superseded)*: Checkpoint at 5beb35b for the owner's trait rulings: 24 adopt, 11 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:156) *(superseded)*: Ours updates invalidated dependencies (SKILL.md:46) but not the tickets themselves; closing rather than deleting keeps the Beads history the brief requires.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:155) *(superseded)*: Ours records each answer (SKILL.md:44) but not the operational facts a task produces for later tickets; the clause on secrets keeps it within AGENTS.md's secre…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:154) *(superseded)*: Ours does authorized prerequisite work (SKILL.md:30) but says nothing for work only the human can do; a precise checklist keeps the wait short.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:153): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already keeps large logs and histories behind references; a wayfinder-spe…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:152): Ours keeps the map low-resolution and loads ticket detail as needed.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:151): Owner deferred the report's reject recommendation, to review the set later: Ours continues into ready tickets while useful and authorized (SKILL.md:49); forcin…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:150): Owner deferred the report's reject recommendation, to review the set later: The initial map follows from the five sections and the charting rules (SKILL.md:16-…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:149) *(superseded)*: Ours settles the destination and tickets sharp questions (SKILL.md:39-41) but sets no order; breadth first keeps an early deep dive from hiding the dependencie…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:148): Owner deferred the report's reject recommendation, to review the set later: Ours already closes an out-of-scope ticket with an explicit exclusion reason (SKILL…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:147): Ours leaves only not-yet-expressible questions in Not yet specified.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:146): Owner deferred the report's reject recommendation, to review the set later: Ours runs a live interview only when one is requested (SKILL.md:29); defaulting to …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:145): Ours resolves a prototype ticket through the prototype skill and records the supporting artifact on the ticket.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:144): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately refuses a competing Markdown tracker when Beads is unavailable (S…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:143): Ours records the answer, closes with evidence and appends a pointer to the map.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:142): Owner deferred the report's reject recommendation, to review the set later: Ours routes a clear route to ordinary planning or execution (SKILL.md:11) instead o…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:141): Ours settles the destination first.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:140): Ours deliberately creates no labels (SKILL.md:24), so the kind lives in the type and title.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:139): Owner deferred the report's reject recommendation, to review the set later: Ours has no research branches (SKILL.md:27); a branch lifecycle rule has nothing to…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:138): Ours deliberately keeps to the Beads rule that the only label is `human` (AGENTS.md, Track durable work).
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:137) *(superseded)*: Ours creates IDs before wiring dependencies.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:136): Owner deferred the report's reject recommendation, to review the set later: Ours makes direct lookups fine and delegation optional (SKILL.md:27); a mandatory s…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:135): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours continues through further authorized ready tickets and explic…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:134): Ours closes out-of-scope tickets with an explicit exclusion reason.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:133): Ours tickets sharp questions even when blocked and graduates newly expressible ones.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:132): Ours deliberately stops at any required human decision (SKILL.md:51-52) rather than classing tickets HITL up front.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:131): Ours has research, prototype, grilling and task kinds.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:130): Ours uses native prerequisite edges between real IDs.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:129): Ours picks the requested or a ready unclaimed child and claims it first.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:128): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours explicitly sizes tickets by decision coherence and dependenci…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:127): Ours's ticket asks one bounded question with a resolution criterion.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:126): Ours's map has the same five sections.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:125): Ours keeps resolution detail on the ticket and a pointer and gist on the map.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:124): Ours references names with IDs or links.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:123): Ours keeps the map a decision graph unless execution was explicitly included.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:122): Ours uses one `Map:` epic with decision tickets as children.
- `2026-08-14` **adopt** (2026-10-14-migration:142): Adopted-in-part: push-right and decision-summary (renamed from 'brief' — documented task-brief collision) into wayfinder, scoped to AFK-internal gates with Pro…
- `2026-08-14` **adopt** (2026-10-14-migration:140): Adopted-in-part: verify-what-you-must-not-run discipline (static trace + CI secret name-matching) into wayfinder's Task ticket type. The 204-line template.sh m…
- `2026-08-12` **adopt** (2026-10-14-migration:106): Copied verbatim (SKILL.md + agents/, ships user-invoked via disable-model-invocation). Adopted as-is per user decision 2026-08-12; local customization (beads-n…
- `2026-08-11` **adopt** (2026-10-14-migration:032) *(superseded)*: The only planner for work larger than one context window under genuine uncertainty: fog-of-war decision tickets resolved one at a time until the route is clear…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
- [skill-comparisons/interaction-utilities](../../../archive/skill-comparisons/interaction-utilities/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `bounded-decision-ticket`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#bounded-decision-ticket` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `breadth-first-charting`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#breadth-first-charting` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `claim-before-work`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#claim-before-work` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `decision-map-epic`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#decision-map-epic` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `dependency-edges`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#dependency-edges` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `destination-first`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#destination-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `fog-hygiene`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#fog-hygiene` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `human-decision-gate`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#live-human-resolution` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `invalidated-ticket-reconciliation`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#invalidated-ticket-reconciliation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `label-free-typing`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#no-triage-labels` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `low-res-map-load`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#low-res-map-load` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `map-as-index`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#map-as-index` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `map-body-sections`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#map-body-sections` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `out-of-scope-close`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#out-of-scope-close` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `plan-not-do`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#plan-not-do` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `prerequisite-task-human-checklist`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#prerequisite-task-human-checklist` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `prerequisite-task-result-facts`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#prerequisite-task-result-facts` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `prototype-ticket-asset`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#prototype-ticket-asset` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `question-graduation`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#question-graduation` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `real-id-wiring`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#real-id-wiring` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2; withdrawn 2026-11-11)
- `record-resolution`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#record-resolution` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `reference-by-name`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#reference-by-name` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `ticket-type-set`:
  - `mattpocock_skills:skill:skills/engineering/wayfinder#ticket-type-set` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/wayfinder#type-directed-resolution` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/engineering/wayfinder#chart-only-session` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours continues into ready tickets while useful and authorized (SKILL.md:49); forcin…
- `mattpocock_skills:skill:skills/engineering/wayfinder#grilling-default-type` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours runs a live interview only when one is requested (SKILL.md:29); defaulting to …
- `mattpocock_skills:skill:skills/engineering/wayfinder#local-tracker-default` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours deliberately refuses a competing Markdown tracker when Beads is unavailable (S…
- `mattpocock_skills:skill:skills/engineering/wayfinder#map-initial-state` (defer): Owner deferred the report's reject recommendation, to review the set later: The initial map follows from the five sections and the charting rules (SKILL.md:16-…
- `mattpocock_skills:skill:skills/engineering/wayfinder#no-map-without-fog` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours routes a clear route to ordinary planning or execution (SKILL.md:11) instead o…
- `mattpocock_skills:skill:skills/engineering/wayfinder#one-ticket-per-session` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours continues through further authorized ready tickets and explic…
- `mattpocock_skills:skill:skills/engineering/wayfinder#out-of-scope-final` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours already closes an out-of-scope ticket with an explicit exclusion reason (SKILL…
- `mattpocock_skills:skill:skills/engineering/wayfinder#research-branch-pr-policy` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours has no research branches (SKILL.md:27); a branch lifecycle rule has nothing to…
- `mattpocock_skills:skill:skills/engineering/wayfinder#research-subagent-branch` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours makes direct lookups fine and delegation optional (SKILL.md:27); a mandatory s…
- `mattpocock_skills:skill:skills/engineering/wayfinder#session-sized-tickets` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours explicitly sizes tickets by decision coherence and dependenci…
- `mattpocock_skills:skill:skills/engineering/wayfinder#ticket-asset-pointers` (defer): Owner deferred the report's reject recommendation, to review the set later: AGENTS.md already keeps large logs and histories behind references; a wayfinder-spe…
<!-- /registry:generated declined -->
