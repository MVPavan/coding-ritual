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

Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology or a ubiquitous language, record an architectural decision, or when another skill needs to maintain the domain model. Trigger on ADR phrases (record, write, supersede an ADR).

**Boundary:** Owns domain terminology, the glossary and ADRs; module structure is codebase-design, and revising a design document is design-evolve.

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
- `glossary-entry-template`: Write glossary entries of a term and its definition, grouped under subheadings when clusters emerge. (Lays the file out as a title and a one-or-two-sentence description, then each term in bold followed by its definition and an Avoid line.)
- `canonical-term-and-aliases`: Pick one preferred term per concept and list its other words as aliases to avoid.
- `tight-concept-definitions`: Define each glossary term tightly by what it is, not what it does. (One or two sentences at most.)
- `context-specific-terms`: Admit only terms specific to the project's context to the glossary, leaving general programming concepts out.
- `context-map-artifact`: Keep a root context map listing each context with its location and purpose and the relationships between contexts.
- `context-map-lookup`: Follow the context map to the right context's glossary when the repository has several.
- `topic-context-resolution`: Infer which context the current topic belongs to, asking when it is unclear.
- `adr-three-gate`: Offer a decision record only when the decision is hard to reverse, surprising without context, and the result of a real trade-off.
- `minimal-decision-record`: Write a decision record as a title and one to three sentences of context, decision and reason.
- `sequential-record-numbering`: Number a new record one above the highest existing number in its folder.
- `optional-record-sections`: Add optional sections to a record, such as status or consequences, only when they carry real information.
- `adr-what-qualifies`: Apply a worked list of decision kinds (architectural shape, integration patterns, lock-in choices, boundaries, deliberate deviations, hidden constraints, non-obvious rejections) that warrant a decision record.
- `adr-match-convention`: Match an existing decision-record convention (location, extension, numbering, headings) before applying defaults, surfacing conflicts instead of adding a second scheme.
- `adr-supersede-lifecycle`: Never delete a decision record; supersede it with a new one and mark the old one superseded.
- `adr-code-gotcha-link`: Leave a short comment at a code trap or constraint linking the decision record that explains it.
- `scoped-decision-records`: Keep system-wide decision records at the repository root and context-specific ones inside each context.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **agent-skills:skill:skills/documentation-and-adrs** `skills/documentation-and-adrs/SKILL.md`
- **mattpocock_skills:skill:skills/engineering/domain-modeling#active-discipline** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#lazy-glossary-and-adr** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#challenge-glossary** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#sharpen-fuzzy** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#concrete-scenarios** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#cross-reference-code** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#update-inline** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#glossary-is-glossary** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#adr-three-gate** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#adr-what-qualifies** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#context-specific-terms** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#scoped-decision-records** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#context-map-artifact** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#context-map-lookup** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#sequential-record-numbering** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#minimal-decision-record** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#optional-record-sections** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#glossary-entry-template** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#canonical-term-and-aliases** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#tight-concept-definitions** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/domain-modeling#topic-context-resolution** `skills/engineering/domain-modeling/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/in-progress/loop-me#sharpen-fuzzy** `skills/in-progress/loop-me/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/engineering/setup-matt-pocock-skills#scoped-decision-records** `skills/engineering/setup-matt-pocock-skills/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/engineering/setup-matt-pocock-skills#context-map-lookup** `skills/engineering/setup-matt-pocock-skills/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
- **mattpocock_skills:skill:skills/engineering/setup-matt-pocock-skills#lazy-glossary-and-adr** `skills/engineering/setup-matt-pocock-skills/SKILL.md` @ 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-11-09` **adopt-merged** (2026-11-09-pocock-4ae2317:155): Checkpoint at 4ae2317 for the owner's trait rulings: 5 adopt, 6 defer, 43 reject.
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:149): Owner ruling 2026-11-09: .claude/skills/domain-modeling/SKILL.md:18 creates the files lazily, only when there is something concrete to write.
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:147): Owner ruling 2026-11-09: .claude/skills/domain-modeling/SKILL.md:15 follows the context map's per-context locations when one exists.
- `2026-11-09` **adopt** (2026-11-09-pocock-4ae2317:119): Owner ruling 2026-11-09: .claude/skills/domain-modeling/CONTEXT-FORMAT.md:65 keeps context-specific decision records in the context and system-wide ones at the…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:562): Checkpoint at 5beb35b for the owner's trait rulings: 21 adopt.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:454): HELD: domain-modeling lists it; ours's grilling routes settled terms to domain-modeling when documentation is requested.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:072): Ours infers the topic's context and asks when it is unclear.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:071): Ours keeps definitions to one or two sentences of what the term is.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:070): Ours picks one term and lists the others under Avoid.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:069): Ours lays entries out as term and definition with an Avoid line, grouped when clusters emerge.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:068): Ours adds status, options or consequences only when they add value.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:067): Ours's template is a title and one to three sentences.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:066): Ours numbers a new ADR one above the highest existing.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:065): Ours follows the context map to the right glossary.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:064): Ours keeps a root context map with locations, purposes and relationships.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:063): Ours keeps context-specific ADRs in each context and system-wide ones at the root.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:062): Ours admits only context-specific terms.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:061): Ours carries the worked list of qualifying decision kinds.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:060): Ours offers an ADR only when all three conditions hold.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:059): Ours keeps the glossary free of implementation detail.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:058): Ours writes a resolved term at once when documentation is authorized and only reports proposals during analysis.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:057): Ours checks stated rules against the code and surfaces contradictions.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:056): Ours stress-tests relationships with invented edge-case scenarios.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:055): Ours proposes a precise canonical term for a vague or overloaded one.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:054): Ours calls out a term that conflicts with the glossary at once.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:053): Ours creates files only when documentation is authorized and there is something to write.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:052): Ours frames the skill as the active discipline of challenging terms, inventing scenarios and writing them down.
- `2026-08-13` **adopt** (2026-10-14-migration:116): Closes the 2026-07-15 deferral. ADR portion absorbed into domain-modeling/ADR-FORMAT.md (convention-first, never-delete/supersede, comment-the-trap-link-the-AD…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:087): Copied verbatim as grill-with-docs' dependency. Also the first skill in bucket 3 (Architecture & Modeling), which was empty - it arrived as a dependency, so it…
- `2026-08-11` **adopt-merged** (2026-10-14-migration:036) *(superseded)*: The only skill maintaining shared vocabulary as an active discipline. Becomes the single home for architecture decision records — the judge found two skills bo…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [2026-11-06-upstream-mattpocock_skills-4ae2317.md](../../reviews/2026-11-06-upstream-mattpocock_skills-4ae2317.md)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `active-discipline`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#active-discipline` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `adr-three-gate`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#adr-three-gate` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `adr-what-qualifies`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#adr-what-qualifies` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `canonical-term-and-aliases`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#canonical-term-and-aliases` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `challenge-glossary`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#challenge-glossary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `concrete-scenarios`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#concrete-scenarios` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `context-map-artifact`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#context-map-artifact` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `context-map-lookup`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#context-map-lookup` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/setup-matt-pocock-skills#context-map-lookup` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
- `context-specific-terms`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#context-specific-terms` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `cross-reference-code`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#cross-reference-code` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `glossary-entry-template`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#glossary-entry-template` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `glossary-is-glossary`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#glossary-is-glossary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `lazy-glossary-and-adr`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#lazy-glossary-and-adr` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/setup-matt-pocock-skills#lazy-glossary-and-adr` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
- `minimal-decision-record`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#minimal-decision-record` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `optional-record-sections`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#optional-record-sections` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `scoped-decision-records`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#scoped-decision-records` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/engineering/setup-matt-pocock-skills#scoped-decision-records` (adopted at 4ae2317ddb22b046e26455e4f9c9b3aaaf62212d)
- `sequential-record-numbering`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#sequential-record-numbering` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `sharpen-fuzzy`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#sharpen-fuzzy` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
  - `mattpocock_skills:skill:skills/in-progress/loop-me#sharpen-fuzzy` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `tight-concept-definitions`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#tight-concept-definitions` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `topic-context-resolution`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#topic-context-resolution` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `update-inline`:
  - `mattpocock_skills:skill:skills/engineering/domain-modeling#update-inline` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
No declined traits recorded.
<!-- /registry:generated declined -->
