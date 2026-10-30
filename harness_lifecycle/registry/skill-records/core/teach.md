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
- `glossary-entry-template`: Write glossary entries of a term and its definition, grouped under subheadings when clusters emerge. (Lays the file out as a title and a one-or-two-sentence description, then each term in bold followed by its definition and an Avoid line.)
- `canonical-term-and-aliases`: Pick one preferred term per concept and list its other words as aliases to avoid.
- `tight-concept-definitions`: Define each glossary term tightly by what it is, not what it does. (One or two sentences at most.)
- `glossary-self-vocabulary`: Use the glossary's own terms inside its other definitions.
- `glossary-admission-on-use`: Add a term to the learner's glossary only once the learner can use it correctly.
- `learning-records`: ADR-like records of lessons and established prior knowledge that steer what to teach next.
- `learning-resource-register`: Keep a course resources file that groups sources into knowledge and community sections and annotates each with what it covers and when to use it.
- `high-trust-resource-filter`: Admit only high-trust sources to the resources file, leaving out marketing posing as education.
- `resource-gap-register`: List the areas the learning goal needs but no good resource covers in a gaps section of the resources file.
- `prune-invalid-resources`: Remove resources that proved wrong, shallow or off-mission rather than keeping them.
- `lesson-format`: Make each lesson short and self-contained, teaching one tightly scoped objective tied to the learner's goal. (Rendered HTML is optional.)
- `reusable-assets`: Reuse existing lesson assets before creating new ones. (Never invents a component library for a single lesson.)
- `quiz-answer-hygiene`: Keep quiz options plausible and free of giveaways, never matched to exact answer length.
- `retrieval-practice`: Have the learner retrieve answers from memory through exercises or questions. (Small exercises or prediction questions, with feedback only after the learner responds.)
- `scope-discipline`: Record progress only within course scope and never treat the repository root as a teaching workspace.
- `sourced-explanations`: Draw explanations from trusted, cited sources and check unfamiliar or changing facts rather than relying on unverified recall.
- `mission-interview-first`: When the learning mission is unclear or empty, ask the learner why they want to learn before teaching.
- `community-opt-out`: Respect the learner's choice not to join communities and record it.
- `learning-record-criteria`: Write a learning record only for demonstrated understanding, disclosed prior knowledge, a corrected misconception or a mission shift, never for coverage, glossary duplicates or activity logs.
- `field-term-resolution`: Record in the glossary how loosely used field terms are resolved in this workspace.
- `in-place-definition-revision`: Revise glossary definitions in place as understanding deepens.
- `mission-document-template`: Write the learning mission as why, success criteria, constraints and out of scope.
- `one-mission-per-workspace`: Keep exactly one mission per learning workspace.
- `one-screen-mission`: Keep the mission document within one screen.
- `minimal-learning-record-template`: Write a learning record as a title and one to three sentences of what was learned and why it matters later.
- `learning-record-supersession`: Mark a contradicted learning record superseded rather than deleting it.
- `cross-linked-lessons`: Cross-link lessons to other lessons and reference documents.
- `domain-vocabulary`: Use the project's established domain vocabulary throughout what you write.
- `sequential-record-numbering`: Number a new record one above the highest existing number in its folder.
- `optional-record-sections`: Add optional sections to a record, such as status or consequences, only when they carry real information.
<!-- /registry:generated traits -->

<!-- registry:generated lineage -->
- **mattpocock_skills:skill:skills/productivity/teach#teaching-workspace** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#mission-grounding** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#proximal-next-lesson** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#storage-strength** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.10)
- **mattpocock_skills:skill:skills/productivity/teach#retrieval-practice** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#spacing** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.10)
- **mattpocock_skills:skill:skills/productivity/teach#lesson-format** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#reusable-assets** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#glossary-admission-on-use** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#learning-records** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#vary-answer-position** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.10)
- **mattpocock_skills:skill:skills/productivity/teach#sourced-explanations** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#knowledge-skills-wisdom-frame** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.10)
- **mattpocock_skills:skill:skills/productivity/teach#cross-linked-lessons** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#mission-interview-first** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#mission-shift-handling** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2 (pending cr-axdt.6.10)
- **mattpocock_skills:skill:skills/productivity/teach#community-opt-out** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#learning-record-criteria** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#field-term-resolution** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#in-place-definition-revision** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#learning-resource-register** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#mission-document-template** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#one-mission-per-workspace** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#one-screen-mission** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#high-trust-resource-filter** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#resource-gap-register** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#prune-invalid-resources** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#minimal-learning-record-template** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#learning-record-supersession** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#glossary-entry-template** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#canonical-term-and-aliases** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#tight-concept-definitions** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#glossary-self-vocabulary** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#domain-vocabulary** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#sequential-record-numbering** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
- **mattpocock_skills:skill:skills/productivity/teach#optional-record-sections** `skills/productivity/teach/SKILL.md` @ 5beb35b040e3de97e54fa9e386d7e42d15c295c2
<!-- /registry:generated lineage -->

<!-- registry:generated history -->
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:591): Owner 2026-10-30 approved the list fix: ours:teach now lists the trait with an approved trait-sharing entry.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:590): Owner 2026-10-30 approved the list fix: ours:teach now lists the trait with an approved trait-sharing entry.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:589): Owner 2026-10-30 approved the list fix: ours:teach now lists the trait with an approved trait-sharing entry.
- `2026-10-30` **adopt-merged** (2026-10-30-mattpocock_skills-5beb35b:584): Checkpoint at 5beb35b for the owner's trait rulings: 36 adopt, 19 defer.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:527): Ours uses the glossary's own terms inside its definitions.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:526): Ours keeps definitions to one or two sentences of what the term is.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:525): Ours picks one term per concept and lists the rest as aliases to avoid.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:524): Ours's glossary has a title, description and bold terms with definitions and Avoid lines, grouped when clusters emerge.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:523): Ours marks a contradicted record superseded instead of deleting it.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:522) *(superseded)*: SHARING: ours:teach has it (.claude/skills/teach/LEARNING-RECORD-FORMAT.md:17-23); listing it needs an owner-approved trait-sharing entry.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:521): Ours's record is a title and one to three sentences.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:520) *(superseded)*: SHARING: ours:teach has it (.claude/skills/teach/LEARNING-RECORD-FORMAT.md:25-27); listing it needs an owner-approved trait-sharing entry.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:519): Ours removes wrong, shallow or off-mission resources.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:518): Ours lists uncovered areas in a Gaps section.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:517): Ours admits only high-trust sources and leaves out marketing posing as education.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:516): Ours keeps the mission within a screen.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:515): Ours keeps one mission per workspace.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:514): Ours's mission template has why, success, constraints and out of scope.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:512): Ours's resources file groups annotated sources into knowledge and community sections.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:511): Ours revises glossary definitions in place as understanding deepens.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:510): Ours records how loosely used field terms resolve in the workspace.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:509): Ours writes a record only for demonstrated understanding, prior knowledge, a corrected misconception or a mission shift.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:508) *(superseded)*: SHARING: ours:teach has it (.claude/skills/teach/GLOSSARY-FORMAT.md:3); listing it needs an owner-approved trait-sharing entry.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:507): Ours records a learner's community opt-out so later sessions stop proposing them.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:506): Owner deferred the report's reject recommendation, to review the set later: Ours uses a small exercise or prediction question when useful (.claude/skills/teach…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:504): Owner deferred the report's reject recommendation, to review the set later: Ours scopes each lesson to one observable objective (.claude/skills/teach/SKILL.md:…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:503): Ours already updates the mission when the user's goal moves (.claude/skills/teach/MISSION-FORMAT.md:30), with the user's authority carried by AGENTS.md:7-12; t…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:502): Ours interviews the learner before writing a mission they cannot articulate.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:501): Owner deferred the report's reject recommendation, to review the set later: Ours invites a focused question after an explanation (.claude/skills/teach/SKILL.md…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:500): Owner deferred the report's reject recommendation, to review the set later: Ours cites the sources behind material claims (.claude/skills/teach/SKILL.md:24-25)…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:499): Ours links useful prior material from each lesson.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:498): Owner deferred the report's reject recommendation, to review the set later: HTML lessons are optional in ours and go through html-artifact (.claude/skills/teac…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:497): Owner deferred the report's reject recommendation, to review the set later: HTML lessons are optional in ours and html-artifact owns their presentation when us…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:496): Owner deferred the report's reject recommendation, to review the set later: Ours checks unfamiliar or changing facts against sources when they arise (.claude/s…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:495): Ours has no course philosophy, so the resources grouping points to one that does not exist (.claude/skills/teach/RESOURCES-FORMAT.md:29); this line delivers th…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:494): Owner deferred the report's reject recommendation, to review the set later: Ours gives feedback after each response (.claude/skills/teach/SKILL.md:21-22), alre…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:493): Ours checks unfamiliar or changing facts and cites material external claims; a course draws explanations from its resources file.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:492): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours records persistent preferences or memory only on explicit req…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:491): Owner deferred the report's reject recommendation, to review the set later: A course in ours keeps its glossary and resources file as reference (.claude/skills…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:490): Owner deferred the report's reject recommendation, to review the set later: Ours answers from checked, cited sources (.claude/skills/teach/SKILL.md:24-25) and …
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:489): Ours bans giveaways in general but never names position; naming it is a concrete, cheap guard.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:488): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours keeps options plausible without matching exact character coun…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:487): Ours's learning records are ADR-like and steer what to teach next.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:486): Ours adds a term only once the learner can use it correctly.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:485): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours does not invent a component library for a single lesson (.cla…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:484): Ours reuses existing assets.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:483): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours makes HTML lessons optional, through html-artifact when the f…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:482): Ours keeps each lesson focused on one observable learning objective.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:481): Carried by the same course-section line as storage-strength.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:480): Ours uses retrieval questions and small exercises, with feedback after the learner responds.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:479): Ours has retrieval questions (.claude/skills/teach/SKILL.md:16-17, .claude/skills/teach/SKILL.md:21-22) but never states the retention goal a multi-session cou…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:478): Deliberate: a course is optional in ours (.claude/skills/teach/SKILL.md:10-11, .claude/skills/teach/SKILL.md:18), so level comes from the conversation first.
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:477): Ours's mission file captures the real reason for learning and every teaching decision traces back to it.
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:476): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours uses a supplied, authorized location and never assumes the re…
- `2026-10-30` **defer** (2026-10-30-mattpocock_skills-5beb35b:475): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours keeps single explanations and walkthroughs stateless and open…
- `2026-10-30` **adopt** (2026-10-30-mattpocock_skills-5beb35b:474): Ours keeps a requested course's mission, resources, learning records and glossary as files in one authorized location.
- `2026-08-14` **adopt** (2026-10-14-migration:148): Adopted VERBATIM as a slash-only work pattern — user ruling 2026-08-14, overriding the analyst reject verdict (skill-comparisons/interaction-utilities/). Ships…
<!-- /registry:generated history -->

<!-- registry:generated reviews -->
- [skill-comparisons/interaction-utilities](../../../archive/skill-comparisons/interaction-utilities/)
<!-- /registry:generated reviews -->

<!-- registry:generated sources -->
- `canonical-term-and-aliases`:
  - `mattpocock_skills:skill:skills/productivity/teach#canonical-term-and-aliases` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `community-opt-out`:
  - `mattpocock_skills:skill:skills/productivity/teach#community-opt-out` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `cross-linked-lessons`:
  - `mattpocock_skills:skill:skills/productivity/teach#cross-linked-lessons` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `domain-vocabulary`:
  - `mattpocock_skills:skill:skills/productivity/teach#domain-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `field-term-resolution`:
  - `mattpocock_skills:skill:skills/productivity/teach#field-term-resolution` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `glossary-admission-on-use`:
  - `mattpocock_skills:skill:skills/productivity/teach#glossary-admission-on-use` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `glossary-entry-template`:
  - `mattpocock_skills:skill:skills/productivity/teach#glossary-entry-template` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `glossary-self-vocabulary`:
  - `mattpocock_skills:skill:skills/productivity/teach#glossary-self-vocabulary` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `high-trust-resource-filter`:
  - `mattpocock_skills:skill:skills/productivity/teach#high-trust-resource-filter` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `in-place-definition-revision`:
  - `mattpocock_skills:skill:skills/productivity/teach#in-place-definition-revision` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `learning-record-criteria`:
  - `mattpocock_skills:skill:skills/productivity/teach#learning-record-criteria` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `learning-record-supersession`:
  - `mattpocock_skills:skill:skills/productivity/teach#learning-record-supersession` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `learning-records`:
  - `mattpocock_skills:skill:skills/productivity/teach#learning-records` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `learning-resource-register`:
  - `mattpocock_skills:skill:skills/productivity/teach#learning-resource-register` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `lesson-format`:
  - `mattpocock_skills:skill:skills/productivity/teach#lesson-format` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `level-adaptation`:
  - `mattpocock_skills:skill:skills/productivity/teach#proximal-next-lesson` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `minimal-learning-record-template`:
  - `mattpocock_skills:skill:skills/productivity/teach#minimal-learning-record-template` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `mission-document-template`:
  - `mattpocock_skills:skill:skills/productivity/teach#mission-document-template` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `mission-grounding`:
  - `mattpocock_skills:skill:skills/productivity/teach#mission-grounding` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `mission-interview-first`:
  - `mattpocock_skills:skill:skills/productivity/teach#mission-interview-first` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `one-mission-per-workspace`:
  - `mattpocock_skills:skill:skills/productivity/teach#one-mission-per-workspace` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `one-screen-mission`:
  - `mattpocock_skills:skill:skills/productivity/teach#one-screen-mission` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `optional-record-sections`:
  - `mattpocock_skills:skill:skills/productivity/teach#optional-record-sections` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `prune-invalid-resources`:
  - `mattpocock_skills:skill:skills/productivity/teach#prune-invalid-resources` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `resource-gap-register`:
  - `mattpocock_skills:skill:skills/productivity/teach#resource-gap-register` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `retrieval-practice`:
  - `mattpocock_skills:skill:skills/productivity/teach#retrieval-practice` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `reusable-assets`:
  - `mattpocock_skills:skill:skills/productivity/teach#reusable-assets` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `sequential-record-numbering`:
  - `mattpocock_skills:skill:skills/productivity/teach#sequential-record-numbering` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `sourced-explanations`:
  - `mattpocock_skills:skill:skills/productivity/teach#sourced-explanations` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `teaching-workspace`:
  - `mattpocock_skills:skill:skills/productivity/teach#teaching-workspace` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
- `tight-concept-definitions`:
  - `mattpocock_skills:skill:skills/productivity/teach#tight-concept-definitions` (adopted at 5beb35b040e3de97e54fa9e386d7e42d15c295c2)
<!-- /registry:generated sources -->

<!-- registry:generated declined -->
- `mattpocock_skills:skill:skills/productivity/teach#always-stateful-course` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours keeps single explanations and walkthroughs stateless and open…
- `mattpocock_skills:skill:skills/productivity/teach#follow-up-prompt` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours invites a focused question after an explanation (.claude/skills/teach/SKILL.md…
- `mattpocock_skills:skill:skills/productivity/teach#html-lessons` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours makes HTML lessons optional, through html-artifact when the f…
- `mattpocock_skills:skill:skills/productivity/teach#just-enough-knowledge` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours scopes each lesson to one observable objective (.claude/skills/teach/SKILL.md:…
- `mattpocock_skills:skill:skills/productivity/teach#lesson-primary-source` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours cites the sources behind material claims (.claude/skills/teach/SKILL.md:24-25)…
- `mattpocock_skills:skill:skills/productivity/teach#open-artifact-for-user` (defer): Owner deferred the report's reject recommendation, to review the set later: HTML lessons are optional in ours and go through html-artifact (.claude/skills/teac…
- `mattpocock_skills:skill:skills/productivity/teach#polished-lesson-typography` (defer): Owner deferred the report's reject recommendation, to review the set later: HTML lessons are optional in ours and html-artifact owns their presentation when us…
- `mattpocock_skills:skill:skills/productivity/teach#preference-notes` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours records persistent preferences or memory only on explicit req…
- `mattpocock_skills:skill:skills/productivity/teach#quiz-equal-length` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours keeps options plausible without matching exact character coun…
- `mattpocock_skills:skill:skills/productivity/teach#reference-sheets` (defer): Owner deferred the report's reject recommendation, to review the set later: A course in ours keeps its glossary and resources file as reference (.claude/skills…
- `mattpocock_skills:skill:skills/productivity/teach#resource-gathering-priority` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours checks unfamiliar or changing facts against sources when they arise (.claude/s…
- `mattpocock_skills:skill:skills/productivity/teach#shared-component-extraction` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours does not invent a component library for a single lesson (.cla…
- `mattpocock_skills:skill:skills/productivity/teach#skill-practice-forms` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours uses a small exercise or prediction question when useful (.claude/skills/teach…
- `mattpocock_skills:skill:skills/productivity/teach#tight-feedback-loop` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours gives feedback after each response (.claude/skills/teach/SKILL.md:21-22), alre…
- `mattpocock_skills:skill:skills/productivity/teach#wisdom-community-referral` (defer): Owner deferred the report's reject recommendation, to review the set later: Ours answers from checked, cited sources (.claude/skills/teach/SKILL.md:24-25) and …
- `mattpocock_skills:skill:skills/productivity/teach#workspace-from-run-dir` (defer): Owner deferred the report's reject recommendation, to review the set later: Opposite stance: ours uses a supplied, authorized location and never assumes the re…
<!-- /registry:generated declined -->
