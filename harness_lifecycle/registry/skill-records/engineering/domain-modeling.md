---
skill: domain-modeling
domain: engineering
stage: Design
substage: Architecture
secondary: []
family: domain-language
aliases: []
status: active
---
# domain-modeling

## Capability

Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology or a ubiquitous language, record an architectural decision, or when another skill needs to maintain the domain model. Trigger on ADR phrases (record, write, supersede an ADR).

<!-- registry:generated traits -->
- `active-discipline`: Actively build the model by challenging terms, inventing scenarios and writing it down, as distinct from merely reading the glossary.
- `declared-glossary-location`: Use the glossary location declared by project instructions, reusing an existing root glossary rather than creating a competing one.
- `lazy-glossary-and-adr`: Create glossary and decision-record files lazily, only when there is something concrete to write.
- `challenge-glossary`: Call out immediately a term that conflicts with the existing glossary language.
- `sharpen-fuzzy`: Propose one precise canonical term for a vague or overloaded one.
- `concrete-scenarios`: Stress-test domain relationships with invented edge-case scenarios that force precision about boundaries.
- `cross-reference-code`: Check whether the code agrees with a stated domain rule and surface contradictions.
- `update-inline`: Write a resolved term into the glossary as soon as it is resolved rather than batching changes.
- `authorized-model-writes`: Edit the glossary and decision records only when documentation work is authorized, otherwise reporting the proposed terms and decisions.
- `glossary-is-glossary`: Keep the glossary free of implementation details and never treat it as a spec or scratchpad.
- `glossary-format`: Write opinionated glossary entries with an Avoid list and tight is-not-does definitions, grouped under subheadings when clusters emerge.
- `context-specific-terms`: Admit only terms specific to the project's context to the glossary, leaving general programming concepts out.
- `multi-context-map`: Maintain a root context map listing contexts, their locations and relationships, inferring which context a topic belongs to or asking.
- `adr-three-gate`: Offer a decision record only when the decision is hard to reverse, surprising without context, and the result of a real trade-off.
- `adr-minimal-template`: Use a one-paragraph decision record with optional status, options and consequences and sequential numbering.
- `adr-what-qualifies`: Apply a worked list of decision kinds (architectural shape, integration patterns, lock-in choices, boundaries, deliberate deviations, hidden constraints, non-obvious rejections) that warrant a decision record.
- `adr-match-convention`: Match an existing decision-record convention (location, extension, numbering, headings) before applying defaults, surfacing conflicts instead of adding a second scheme.
- `adr-supersede-lifecycle`: Never delete a decision record; supersede it with a new one and mark the old one superseded.
- `adr-code-gotcha-link`: Leave a short comment at a code trap or constraint linking the decision record that explains it.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/engineering/domain-modeling** `reference_harnesses/mattpocock_skills/skills/engineering/domain-modeling/SKILL.md` @ 84fdeff
  - merged from: documentation-and-adrs (ADR portion)
  - modified: absorb ADR convention detection and the never-delete/supersede lifecycle
  - modified: absorb one line from the gotchas section: comment the trap, link the ADR
- **mattpocock_skills:skill:skills/engineering/domain-modeling** `skills/engineering/domain-modeling/SKILL.md`
  - merged from: documentation-and-adrs (ADR portion)
  - modified: absorb ADR convention detection and the never-delete/supersede lifecycle
  - modified: absorb one line from the gotchas section: comment the trap, link the ADR
- **agent-skills:skill:skills/documentation-and-adrs** `skills/documentation-and-adrs/SKILL.md`
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-13` **adopt** (2026-10-14-migration:116): Closes the 2026-07-15 deferral. ADR portion absorbed into domain-modeling/ADR-FORMAT.md (convention-first, never-delete/supersede, comment-the-trap-link-the-AD…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:087): Copied verbatim as grill-with-docs' dependency. Also the first skill in bucket 3 (Architecture & Modeling), which was empty - it arrived as a dependency, so it…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:036) *(superseded)*: The only skill maintaining shared vocabulary as an active discipline. Becomes the single home for architecture decision records — the judge found two skills bo…
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
