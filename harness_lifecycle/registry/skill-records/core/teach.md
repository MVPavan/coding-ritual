---
skill: teach
domain: core
stage: U
substage: Tutoring
secondary: []
family: learning-content
aliases: [teach-session]
status: active
---
# teach

Teach a concept, walk through a session, or conduct an explicitly requested ongoing course.

<!-- registry:generated traits -->
- `learning-shape`: Choose one of a single concept explanation, a session walkthrough, or an explicitly requested ongoing course.
- `level-adaptation`: Infer the learner's level from the conversation and adjust from their responses.
- `what-vs-why`: Separate what happened from why it was chosen when explaining.
- `teaching-workspace`: Keep a multi-session course's state (mission, resources, learning records, glossary and lessons) as files in one course workspace.
- `authorized-course-location`: Open a course workspace only for an explicitly requested ongoing course, in an authorized supplied location, creating its files lazily.
- `mission-grounding`: A mission document capturing the concrete real-world reason for learning that anchors every teaching choice.
- `glossary-format`: Write opinionated glossary entries with an Avoid list and tight is-not-does definitions, grouped under subheadings when clusters emerge. (Uses the glossary's own terms inside definitions.)
- `glossary-admission-on-use`: Add a term to the learner's glossary only once the learner can use it correctly.
- `learning-records`: ADR-like records of lessons and established prior knowledge that steer what to teach next.
- `resources-curation`: A curated, annotated set of high-trust knowledge and community sources, with gaps surfaced explicitly.
- `lesson-format`: Make each lesson short and self-contained, teaching one tightly scoped objective tied to the learner's goal. (Rendered HTML is optional.)
- `reusable-assets`: Reuse existing lesson assets before creating new ones. (Never invents a component library for a single lesson.)
- `quiz-answer-hygiene`: Keep quiz options plausible and free of giveaways, never matched to exact answer length.
- `retrieval-practice`: Have the learner retrieve answers from memory through exercises or questions. (Small exercises or prediction questions, with feedback only after the learner responds.)
- `scope-discipline`: Record progress only within course scope and never treat the repository root as a teaching workspace.
- `sourced-explanations`: Draw explanations from trusted, cited sources and check unfamiliar or changing facts rather than relying on unverified recall.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/productivity/teach** `skills/productivity/teach/SKILL.md` @ 84fdeff
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-08-14` **adopt** (2026-10-14-migration:148): Adopted VERBATIM as a slash-only work pattern — user ruling 2026-08-14, overriding the analyst reject verdict (skill-comparisons/interaction-utilities/). Ships…
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
