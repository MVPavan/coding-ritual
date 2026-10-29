---
skill: improve-codebase-architecture
domain: engineering
stage: Operations
substage: Maintenance
secondary: []
family: architecture-audit
aliases: []
status: active
---
# improve-codebase-architecture

## Capability

Find evidence-backed architecture improvements within a named area or requested codebase survey.

<!-- registry:generated traits -->
- `scope-by-evidence`: Scope the audit to a named module or pain point, otherwise to the hot spots in recent change history. (Also weighs actual maintenance and test friction when choosing areas.)
- `friction-signals`: Surface architectural friction that current code actually supports rather than speculative smells.
- `deletion-test`: Question a layer that only forwards and keep one whose removal would spread complexity across callers. (Used as a candidate-finding signal: does complexity disappear or merely move into callers.)
- `candidate-comparison`: Give each candidate its files, friction, direction, benefit, migration cost, evidence and confidence, then present a concise comparison and the strongest supported recommendation.
- `optional-report`: Produce a standalone HTML report only when requested or clearly helpful, delegating presentation to the shared artifact skill and requiring any before/after diagram to show a real structural difference.
- `module-vocabulary`: Reason about design with a shared deep-module glossary: module, interface, depth, seam, adapter and locality.
- `project-term-allowance`: Let the project's own precise terms, such as API, service or boundary, stand beside the design glossary rather than banning them.
- `adr-conflict-callout`: When a candidate conflicts with a decision record, explain the new evidence that might justify revisiting it.
- `review-no-auto-followup`: Do not automatically enter a grilling loop, interview, alternative-design exercise or domain-document update after delivering the review; each happens only when requested or already authorized.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture** `reference_harnesses/mattpocock_skills/skills/engineering/improve-codebase-architecture/SKILL.md` @ 84fdeff
  - modified: demote the mandatory HTML report to optional — it pulls Tailwind and Mermaid from a CDN, a network dependency
  - modified: move the load-bearing parts inline: recommendation-strength badges and the vocabulary discipline
- **mattpocock_skills:skill:skills/engineering/improve-codebase-architecture** `skills/engineering/improve-codebase-architecture/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-13` **adopt** (2026-10-14-migration:118): Adopted verbatim per user ruling 2026-08-13 (SKILL + HTML-REPORT; agents/openai.yaml excluded), overriding the council's demote-the-CDN-report change — user wi…
- `2026-08-11` **adopt** (2026-10-14-migration:037) *(superseded)*: The only skill that FINDS restructuring candidates rather than applying a known one, scoped by commit-history hot spots. It consumes codebase-design's vocabula…
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
